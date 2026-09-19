import io
from pathlib import Path

import pytest
from PIL import Image, ImageChops
from pypdf import PdfReader, PdfWriter

from chsi_translator.extract import ExtractionError, extract_report
from chsi_translator.export import export_pdf, layout_rows
from chsi_translator.model import Field, Report
from chsi_translator.selftest import make_fixture
from chsi_translator.translate import online_candidates, translate_field, translate_online


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "中文报告.pdf"
    make_fixture(path)
    return path


def test_end_to_end_offline(sample, tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Default import must remain offline")
    monkeypatch.setattr("chsi_translator.translate.urlopen", no_network)
    r = extract_report(sample)
    assert r.value("name") == "ZHANG SAN"
    assert r.value("major") == "Computer Science and Technology"
    assert r.value("verification_code") == "DEMO0TEST12345678"
    assert r.get("expiry") is None
    assert r.get("college").source == ""
    assert r.get("department").source == "软件研究所"
    assert not r.blockers()
    pdf = PdfReader(io.BytesIO(export_pdf(r)))
    assert len(pdf.pages) == 1
    text = pdf.pages[0].extract_text()
    assert "Institute of Software" in text and "Department / Institute" in text
    assert "College" in text  # Keep the blank row that exists in the source.
    assert "Student Record" in text and "ZHANG SAN" in text
    assert "1 to 6 months" in text and "1 year" not in text
    assert "Date of Expiry" not in text
    assert len(r.notes) == 4
    # Compare source image pixels with exported image pixels, not only filenames.
    output_images = [im.image.convert("RGB") for im in pdf.pages[0].images]
    source_images = [im.image.convert("RGB") for im in PdfReader(sample).pages[0].images]
    for source in source_images:
        candidates = [im for im in output_images if im.size == source.size]
        assert any(ImageChops.difference(source, im).getbbox() is None for im in candidates)
    r.get("name").translated = "ZHANG SAN CALIBRATED"
    r.get("name").status = "manual"
    r.save(tmp_path / "校准.chsi.json")
    loaded = Report.load(tmp_path / "校准.chsi.json")
    assert loaded.photo == r.photo and loaded.qr == r.qr
    assert loaded.source_sha256 == r.source_sha256
    assert loaded.get("name").source == "张三"
    assert "ZHANG SAN CALIBRATED" in PdfReader(io.BytesIO(export_pdf(loaded))).pages[0].extract_text()


def test_wrapped_chinese_and_blank_row(tmp_path):
    path = tmp_path / "wrapped.pdf"
    make_fixture(path, wrapped=True)
    r = extract_report(path)
    assert r.get("major").source == "计算机科学与技术"
    assert r.value("major") == "Computer Science and Technology"
    assert r.get("college").source == ""


def test_unknown_value_blocks_until_calibrated(tmp_path):
    path = tmp_path / "unknown.pdf"
    make_fixture(path, unknown_major=True)
    r = extract_report(path)
    assert r.get("major").status == "pending"
    assert [f.key for f in online_candidates(r)] == ["major"]
    with pytest.raises(ValueError, match="校准"):
        export_pdf(r)
    r.get("major").translated, r.get("major").status = "A Reviewed Subject", "manual"
    assert export_pdf(r).startswith(b"%PDF")


@pytest.mark.parametrize("value,expected", [("2024年02月29日", "Feb. 29, 2024"), ("2023/02/29", ""), ("2026-09-18", "Sep. 18, 2026")])
def test_dates_validated(value, expected):
    f = Field("birth", "出生日期", "Date of Birth", value)
    translate_field(f)
    assert f.translated == expected


def test_composite_surname():
    f = Field("name", "姓名", "Name", "欧阳明")
    translate_field(f)
    assert f.translated == "OUYANG MING" and f.status == "review"


def test_multiple_reports_rejected(sample, tmp_path):
    writer = PdfWriter()
    writer.append(sample)
    writer.append(sample)
    path = tmp_path / "multiple.pdf"
    writer.write(path)
    with pytest.raises(ExtractionError, match="多份"):
        extract_report(path)


def test_encrypted_pdf(sample, tmp_path):
    writer = PdfWriter(clone_from=sample)
    writer.encrypt("test-password")
    path = tmp_path / "locked.pdf"
    writer.write(path)
    with pytest.raises(ExtractionError, match="加密"):
        extract_report(path)
    assert extract_report(path, "test-password").value("name") == "ZHANG SAN"


def test_unrelated_and_corrupt_files(tmp_path):
    path = tmp_path / "other.pdf"
    make_fixture(path, title=False)
    with pytest.raises(ExtractionError, match="没有识别"):
        extract_report(path)
    path.write_bytes(b"not a pdf")
    with pytest.raises(ExtractionError, match="有效 PDF"):
        extract_report(path)


def test_oversized_value_cannot_overflow_template(sample):
    r = extract_report(sample)
    for f in r.fields:
        if f.key in {"major", "institution", "department"}:
            f.translated = "Long academic terminology " * 22 + "ENDMARKER"
    with pytest.raises(ValueError, match="超出模板"):
        export_pdf(r)


def test_chinese_in_english_field_rejected(sample):
    r = extract_report(sample)
    r.get("major").translated = "仍然是中文"
    with pytest.raises(ValueError, match="仍包含中文"):
        export_pdf(r)


def test_html_like_input_remains_literal(sample):
    r = extract_report(sample)
    r.get("major").translated = "<b>Literal text</b> & Research"
    text = PdfReader(io.BytesIO(export_pdf(r))).pages[0].extract_text()
    assert "<b>Literal text</b> & Research" in text


def test_online_errors_do_not_become_translations(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, *args): return b'{"responseStatus":429,"responseData":{"translatedText":"LIMIT EXCEEDED"}}'
    monkeypatch.setattr("chsi_translator.translate.urlopen", lambda *a, **k: Response())
    with pytest.raises(ValueError, match="配额"):
        translate_online("学校")


def test_missing_field_cannot_be_hidden_by_empty_value():
    report = Report(fields=[Field("major", "专业", "Major", "", present=False, status="missing", visible=True)])
    assert report.blockers()


def test_draft_schema_rejected(tmp_path):
    path = tmp_path / "bad.chsi.json"
    path.write_text('{"schema_version":99}', encoding="utf-8")
    with pytest.raises(ValueError, match="版本"):
        Report.load(path)


def test_original_protected_even_after_draft_restore(sample, tmp_path):
    r = extract_report(sample)
    original = sample.read_bytes()
    r.save(tmp_path / "portable.chsi.json")
    loaded = Report.load(tmp_path / "portable.chsi.json")
    with pytest.raises(ValueError, match="不能覆盖"):
        export_pdf(loaded, sample)
    assert sample.read_bytes() == original


def test_modified_source_note_is_not_silently_replaced():
    f = Field("note_4", "注意事项 4", "Source note 4", "期限为1~6个月，但不可延长。")
    translate_field(f)
    assert f.translated == "" and f.status == "pending"


def test_visibility_draft_and_legacy_migration(sample, tmp_path):
    import json
    r = extract_report(sample)
    r.get("college").visible = False
    r.save(tmp_path / "draft.json")
    restored = Report.load(tmp_path / "draft.json")
    assert not restored.get("college").shown
    pdf = PdfReader(io.BytesIO(export_pdf(restored)))
    assert len(pdf.pages) == 1
    assert "Institute of Software" in pdf.pages[0].extract_text()
    assert "College" not in pdf.pages[0].extract_text()
    data = json.loads((tmp_path / "draft.json").read_text("utf-8"))
    data["include_appendix"] = False
    data["schema_version"] = 1
    for f in data["fields"] + data["notes"]:
        del f["visible"]
    (tmp_path / "draft.json").write_text(json.dumps(data), encoding="utf-8")
    migrated = Report.load(tmp_path / "draft.json")
    assert migrated.get("college").shown and migrated.get("department").shown
    assert not migrated.get("student_id").shown


def test_template_graphics_unchanged_outside_fill_regions(sample):
    import pypdfium2 as pdfium
    from PIL import ImageDraw
    from chsi_translator.export import ASSETS
    original = pdfium.PdfDocument(ASSETS.joinpath("report_template.pdf").read_bytes())
    output = pdfium.PdfDocument(export_pdf(extract_report(sample)))
    a = original[0].render(scale=2).to_pil().convert("RGB")
    b = output[0].render(scale=2).to_pil().convert("RGB")
    diff = ImageChops.difference(a, b)
    mask = ImageDraw.Draw(diff)
    h = float(original[0].get_height())
    # Permit the complete table (including labels) to reflow.
    for x0, y0, x1, y1 in [(179, 741, 539, 755), (58, 244, 538, 724),
                          (74, 154, 145, 226), (161, 199, 536, 215), (60, 39, 501, 95)]:
        mask.rectangle((int(x0*2), int((h-y1)*2), int(x1*2+2), int((h-y0)*2+2)), fill="black")
    assert diff.getbbox() is None
    original.close()
    output.close()


def test_template_has_no_example_identity_or_images():
    from chsi_translator.export import ASSETS
    page = PdfReader(io.BytesIO(ASSETS.joinpath("report_template.pdf").read_bytes())).pages[0]
    text = page.extract_text()
    assert "GUO TONGYI" not in text and "AHMU8CTY2X2AN7UE" not in text
    assert "Xiamen University" not in text and "Date of Expiry" not in text
    assert len(page.images) == 6
    assert {image.image.size for image in page.images}.isdisjoint({(480, 640), (147, 147)})


def test_values_use_upstream_font_size_and_coordinates(sample):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(export_pdf(extract_report(sample)))) as pdf:
        words = pdf.pages[0].extract_words(extra_attrs=["size", "fontname"])
        name = next(w for w in words if w["text"] == "ZHANG")
        assert name["x0"] == pytest.approx(180)
        assert name["size"] == pytest.approx(8.6)
        assert "Roboto-Regular" in name["fontname"]
        code = next(w for w in words if w["text"] == "DEMO0TEST12345678")
        assert code["x0"] == pytest.approx(252)
        assert code["size"] == pytest.approx(10)
        assert "Roboto-Medium" in code["fontname"]


def test_calibrated_notes_replace_template_text(sample):
    r = extract_report(sample)
    r.notes[-1].translated = "The validity period is specified by the report owner."
    text = PdfReader(io.BytesIO(export_pdf(r))).pages[0].extract_text()
    assert r.notes[-1].translated in text
    assert "1 year" not in text and "1 to 6 months" not in text


def test_long_field_wraps_inside_its_row(sample):
    r = extract_report(sample)
    r.get("major").translated = "Computer Science and Technology with Specialization in Distributed Systems and Information Engineering"
    pdf = PdfReader(io.BytesIO(export_pdf(r)))
    assert len(pdf.pages) == 1
    assert "Information Engineering" in pdf.pages[0].extract_text()


def test_default_fields_follow_source_including_blank_rows(sample):
    r = extract_report(sample)
    assert [row.item.key for row in layout_rows(r)] == [
        "name", "sex", "birth", "ethnicity", "institution", "level", "major", "duration",
        "education", "learning", "college", "department", "start", "status", "graduation"]
    assert r.get("college").shown and r.get("college").translated == ""
    assert not r.get("class").shown and not r.get("student_id").shown


def test_hiding_rows_removes_labels_values_and_vertical_gaps(sample):
    r = extract_report(sample)
    before = {row.item.key: row.y for row in layout_rows(r)}
    r.get("college").visible = r.get("department").visible = False
    after = {row.item.key: row.y for row in layout_rows(r)}
    assert after["start"] == pytest.approx(before["start"] + 56)
    text = PdfReader(io.BytesIO(export_pdf(r))).pages[0].extract_text()
    assert "College" not in text and "Department / Institute" not in text
    assert "Institute of Software" not in text
    assert "Start Date" in text


def test_hiding_early_fields_moves_long_values_safely_around_photo(sample):
    r = extract_report(sample)
    for key in ("name", "sex", "birth", "ethnicity"):
        r.get(key).visible = False
    r.get("institution").translated = "International University of Computer Science and Advanced Information Technology"
    rows = layout_rows(r)
    assert rows[0].item.key == "institution" and len(rows[0].values) >= 2
    assert rows[1].y < rows[0].y - rows[0].leading
    assert export_pdf(r).startswith(b"%PDF")


def test_all_supported_fields_remain_one_page_and_do_not_overlap(sample):
    r = extract_report(sample)
    r.get("class").translated, r.get("class").visible = "Computer Science Class 1", True
    r.get("student_id").translated, r.get("student_id").visible = "DEMO-123456789", True
    r.get("major").translated = "Computer Science and Technology with Specialization in Distributed Systems and Information Engineering"
    rows = layout_rows(r)
    assert len(rows) == 17
    for a, b in zip(rows, rows[1:]):
        assert a.y - (max(len(a.labels), len(a.values))-1) * a.leading - a.size * .3 > b.y + b.size * .8
    last = rows[-1]
    assert last.y - (max(len(last.labels), len(last.values))-1) * last.leading - last.size * .3 >= 246
    pdf = PdfReader(io.BytesIO(export_pdf(r)))
    assert len(pdf.pages) == 1
    assert "Computer Science Class 1" in pdf.pages[0].extract_text()
    assert "DEMO-123456789" in pdf.pages[0].extract_text()


def test_hidden_pending_fields_do_not_block_and_can_be_restored(sample):
    r = extract_report(sample)
    r.get("major").translated, r.get("major").status, r.get("major").visible = "", "pending", False
    assert not r.blockers() and export_pdf(r)
    assert online_candidates(r) == []
    r.reset_visibility()
    assert r.get("major").shown and r.blockers()
    assert not r.get("student_id").shown


def test_dates_code_and_notes_can_be_hidden_without_stale_text(sample):
    r = extract_report(sample)
    for key in ("renewal", "verification_code", "note_4"):
        r.get(key).visible = False
    text = PdfReader(io.BytesIO(export_pdf(r))).pages[0].extract_text()
    for text_not_expected in ("Date of Renewal", "Online Verification Code", "DEMO0TEST12345678", "1 to 6 months"):
        assert text_not_expected not in text


def test_manual_source_order_is_preserved(sample):
    r = extract_report(sample)
    r.fields[0], r.fields[1] = r.fields[1], r.fields[0]
    r.ensure_field_options()
    assert [row.item.key for row in layout_rows(r)][:2] == ["sex", "name"]
