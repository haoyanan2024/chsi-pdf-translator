from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader

from .model import Field, Report, REQUIRED, SPECS
from .translate import translate_report


class ExtractionError(ValueError):
    """A readable PDF could not be identified unambiguously as a student report."""


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _lines(page) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for word in sorted(page.extract_words(x_tolerance=2, y_tolerance=3), key=lambda w: (w["top"], w["x0"])):
        if not lines or abs(word["top"] - lines[-1][0]["top"]) > 3.5:
            lines.append([word])
        else:
            lines[-1].append(word)
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def _anchor(line, width):
    if line[0]["x0"] > width * .32:
        return None
    for key, aliases, label in SPECS:
        for alias in sorted(aliases, key=len, reverse=True):
            for end in range(1, min(8, len(line)) + 1):
                prefix = compact("".join(w["text"] for w in line[:end])).rstrip(":：")
                if prefix == alias:
                    return key, alias, label, end, ""
            # Some producers put label and value in the same PDF text word.
            m = re.match(r"^" + re.escape(alias) + r"[:：](.+)$", line[0]["text"])
            if m:
                return key, alias, label, 1, m.group(1)
    return None


def parse_fields(page) -> tuple[list[Field], list[str]]:
    lines = _lines(page)
    anchors = [(i, _anchor(line, page.width)) for i, line in enumerate(lines)
               if page.height * .11 < line[0]["top"] < page.height * .77]
    anchors = [(i, a) for i, a in anchors if a]
    if len(anchors) < 5:
        raise ExtractionError("无法识别报告字段布局，请使用学信网直接下载的中文学籍报告 PDF。")
    fields, warnings, seen = [], [], set()
    starts = [lines[i][a[3]]["x0"] for i, a in anchors if len(lines[i]) > a[3]]
    value_x = sorted(starts)[len(starts) // 2] if starts else page.width * .3
    for n, (i, anchor) in enumerate(anchors):
        key, label, english_label, count, inline = anchor
        if key in seen:
            raise ExtractionError(f"检测到重复字段“{label}”，无法安全判断其归属。请使用单份原始报告。")
        seen.add(key)
        values = [inline] if inline else []
        values += [word["text"] for word in lines[i][count:]]
        end = anchors[n + 1][0] if n + 1 < len(anchors) else i + 1
        for continuation in lines[i + 1:end]:
            # Don't pull empty-field values from a later row or a footer.
            if (continuation[0]["top"] - lines[i][0]["top"] < 55
                    and continuation[0]["x0"] >= value_x - 8):
                values.extend(word["text"] for word in continuation)
            elif continuation[0]["x0"] < value_x - 8:
                warnings.append("发现未识别的表格行：" + " ".join(w["text"] for w in continuation))
        source = " ".join(values).strip()
        # PDF text often splits each Chinese glyph; join only adjacent Chinese glyphs.
        source = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", source)
        fields.append(Field(key, label, english_label, source))
    for key, aliases, label in SPECS:
        if key in REQUIRED and key not in seen:
            fields.append(Field(key, aliases[0], label, "", present=False, visible=True))
    return fields, warnings


def render_page(source: str | Path | bytes, page_index=0, scale=1.35) -> bytes:
    with pdfium.PdfDocument(str(source) if isinstance(source, Path) else source) as doc:
        page = doc[page_index]
        if page.get_width() > 2500 or page.get_height() > 3500:
            raise ExtractionError("页面尺寸过大，无法预览。")
        bitmap = page.render(scale=scale)
        result = io.BytesIO()
        bitmap.to_pil().convert("RGB").save(result, "PNG")
        bitmap.close()
        page.close()
        return result.getvalue()


def _get_images(page, reader_page) -> tuple[bytes | None, bytes | None]:
    width, height = page.width, page.height
    images = [im for im in page.images if 15 < im["x1"] - im["x0"] < width * .35
              and 15 < im["bottom"] - im["top"] < height * .35]
    portraits = [im for im in images if im["x0"] > width * .55 and im["top"] < height * .5
                 and .4 < (im["x1"] - im["x0"]) / (im["bottom"] - im["top"]) < 1.1]
    squares = [im for im in images if im["top"] > height * .50
               and .85 < (im["x1"] - im["x0"]) / (im["bottom"] - im["top"]) < 1.15]

    def extract(candidates):
        if not candidates:
            return None
        candidate = max(candidates, key=lambda im: (im["x1"] - im["x0"]) * (im["bottom"] - im["top"]))
        size = tuple(candidate.get("srcsize", ()))
        # Prefer original bitmap bytes, retaining every QR module and photo pixel.
        try:
            matching = [im for im in reader_page.images if im.image.size == size]
            if len(matching) == 1:
                out = io.BytesIO()
                matching[0].image.convert("RGB").save(out, "PNG")
                return out.getvalue()
        except (ValueError, NotImplementedError, OSError):
            pass
        crop = page.crop((candidate["x0"], candidate["top"], candidate["x1"], candidate["bottom"]))
        out = io.BytesIO()
        crop.to_image(resolution=250).original.save(out, "PNG")
        return out.getvalue()

    return extract(portraits), extract(squares)


def extract_report(path: str | Path, password: str | None = None) -> Report:
    path = Path(path)
    if path.stat().st_size > 30_000_000:
        raise ExtractionError("文件超过 30 MB，请使用学信网直接下载的报告。")
    data = path.read_bytes()
    if not data.lstrip().startswith(b"%PDF-"):
        raise ExtractionError("所选文件不是有效 PDF。")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(password or ""):
            raise ExtractionError("PDF 已加密，请先用密码解密并另存为可读取的 PDF。")
        if len(reader.pages) > 30:
            raise ExtractionError("PDF 页数过多，请选择单份学籍报告。")
        with pdfplumber.open(io.BytesIO(data), password=password) as pdf:
            matches = []
            for index, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                header = page.crop((0, 0, page.width, page.height * .13)).extract_text() or ""
                if "学籍在线验证报告" in compact(header):
                    matches.append((index, text))
            if not matches:
                raise ExtractionError("没有识别到中文《教育部学籍在线验证报告》。扫描件、图片 PDF 和学历备案表暂不支持；请使用学信网原始下载文件。")
            if len(matches) != 1:
                raise ExtractionError("文件包含多份报告，请分别导入，避免混用个人资料。")
            index, text = matches[0]
            page = pdf.pages[index]
            fields, warnings = parse_fields(page)
            report = Report(fields=fields, source_name=path.name, source_sha256=hashlib.sha256(data).hexdigest(),
                            page_index=index, warnings=warnings)
            tight = compact(text)
            for key, label, en in [("renewal", "更新日期", "Date of Renewal"), ("expiry", "失效日期", "Date of Expiry")]:
                labels = "(?:失效日期|有效期至|有效期截止日期|到期日期)" if key == "expiry" else "(?:更新日期|报告日期)"
                match = re.search(labels + r"[:：]?(\d{4}[年/.-]\d{1,2}[月/.-]\d{1,2}日?)", tight)
                if match:
                    report.fields.append(Field(key, label, en, match.group(1)))
            codes = re.findall(r"(?<![A-Za-z0-9])([A-Z0-9]{12,24})(?![A-Za-z0-9])", text)
            code_anchor = next((line for line in _lines(page) if "在线验证码" in compact("".join(w["text"] for w in line))), None)
            if code_anchor:
                nearby = " ".join(w["text"] for line in _lines(page) for w in line
                                  if abs(w["top"] - code_anchor[0]["top"]) < 24)
                local = re.findall(r"(?<![A-Za-z0-9])([A-Z0-9]{12,24})(?![A-Za-z0-9])", nearby)
                if local:
                    codes = local
            codes = list(dict.fromkeys(codes))
            if len(codes) == 1:
                report.fields.append(Field("verification_code", "在线验证码", "Online Verification Code", codes[0]))
            else:
                report.fields.append(Field("verification_code", "在线验证码", "Online Verification Code", "", present=False))
                report.warnings.append("验证码未能唯一识别，请从原文校准；不要把数字 0 改为字母 O。")
            url = re.search(r"https?://(?:www\.)?chsi\.com\.cn/[^\s\u3400-\u9fff]+", text)
            if url:
                report.verification_url = url.group(0).rstrip("。；，)")
            if "注意事项" in text:
                note_text = re.split(r"注意事项\s*[:：]?", text, maxsplit=1)[1]
                for num, match in enumerate(re.finditer(r"(?:^|\n)\s*\d+[、.．]\s*(.*?)(?=\n\s*\d+[、.．]|\Z)", note_text, re.S), 1):
                    content = re.sub(r"\s*\n\s*", "", match.group(1)).strip()
                    report.notes.append(Field(f"note_{num}", f"注意事项 {num}", f"Source note {num}", content))
            report.photo, report.qr = _get_images(page, reader.pages[index])
            for name, asset in [("证件照", report.photo), ("二维码", report.qr)]:
                if not asset:
                    report.warnings.append(f"未能自动提取{name}，可在界面中补充。")
            # Render decrypted bytes if needed; no temporary plaintext file is created.
            if reader.is_encrypted:
                from pypdf import PdfWriter
                stream = io.BytesIO()
                writer = PdfWriter()
                writer.append_pages_from_reader(reader)
                writer.write(stream)
                report.preview = render_page(stream.getvalue(), index)
            else:
                report.preview = render_page(data, index)
            translate_report(report)
            report.ensure_field_options()
            return report
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("无法读取 PDF：文件可能损坏、加密或使用不支持的布局。" + f" ({type(exc).__name__})") from exc


def load_asset(path: str | Path) -> bytes:
    with Image.open(path) as im:
        if im.width * im.height > 25_000_000:
            raise ValueError("图片尺寸过大。")
        out = io.BytesIO()
        im.convert("RGB").save(out, "PNG")
        return out.getvalue()
