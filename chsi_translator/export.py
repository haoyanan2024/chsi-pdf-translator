"""Lay out selected source fields on muxiymmm's ornamental template.

The bundled template is visually identical to upstream, with hidden example
identity text/photo/QR removed. See data/TEMPLATE_PROVENANCE.md.
"""
from __future__ import annotations

import io
import re
import threading
from importlib.resources import files
from pathlib import Path
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .model import Field, Report, _atomic_write

ASSETS = files("chsi_translator").joinpath("data")
FONT = "CHSI-Roboto-Regular"
MEDIUM = "CHSI-Roboto-Medium"
_FONT_LOCK = threading.Lock()


def register_fonts():
    with _FONT_LOCK:
        for name, filename in ((FONT, "Roboto-Regular.ttf"), (MEDIUM, "Roboto-Medium.ttf")):
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, io.BytesIO(ASSETS.joinpath("fonts/" + filename).read_bytes())))


def _fit(can, text, x, y, width, *, size=8.6, minimum=7, font=FONT, label="字段", lines=1):
    """Keep normal values at upstream size; fit long values within their cell."""
    text = re.sub(r"[\r\n\t]+", " ", text).strip()
    if not text:
        return
    for char in text:
        if ord(char) not in pdfmetrics.getFont(font).face.charToGlyph:
            raise ValueError(f"{label} 包含模板字体不支持的字符 {char!r}，请校准后导出。")
    if pdfmetrics.stringWidth(text, font, size) <= width:
        can.setFont(font, size)
        can.drawString(x, y, text)
        return
    if lines > 1:
        words, rows, current = text.split(), [], ""
        for word in words:
            trial = (current + " " + word).strip()
            if pdfmetrics.stringWidth(trial, font, size) <= width:
                current = trial
            else:
                if current:
                    rows.append(current)
                current = word
        if current:
            rows.append(current)
        if len(rows) <= lines and all(pdfmetrics.stringWidth(row, font, size) <= width for row in rows):
            can.setFont(font, size)
            for index, row in enumerate(rows):
                can.drawString(x, y - index * 10, row)
            return
    fitted = min(size, width / pdfmetrics.stringWidth(text, font, 1))
    if fitted < minimum:
        raise ValueError(f"{label} 的译文超出模板固定区域，请缩短译文后再导出。")
    can.setFont(font, fitted)
    can.drawString(x, y, text)


def _clear_variable_text(page):
    # Remove original table labels, source notes and code label as PDF drawing
    # operations. Background and border remain intact, without cover rectangles.
    content = page.get_contents()
    operations, suppress = [], False
    for operands, op in content.operations:
        if op == b"BT":
            suppress = False
        if op == b"Tm":
            x, y = float(operands[4]), float(operands[5])
            suppress = ((abs(x - 62) < .1 and y in (87, 72, 57, 42))
                        or (abs(x - 60) < .1 and 370 < y < 720)
                        or (abs(x - 163.79) < .1 and abs(y - 202.18) < .1))
        if suppress and op in {b"Tj", b"TJ", b"'", b'"'}:
            continue
        operations.append((operands, op))
    content.operations = operations
    page.replace_contents(content)


@dataclass
class RowLayout:
    item: Field
    y: float
    labels: list[str]
    values: list[str]
    size: float
    leading: float


def _wrap(text: str, width: float, size: float) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return [""]
    # Split even unspaced IDs/long terms, keeping every character.
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if pdfmetrics.stringWidth(trial, FONT, size) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = ""
        for char in word:
            if current and pdfmetrics.stringWidth(current + char, FONT, size) > width:
                lines.append(current)
                current = ""
            current += char
    if current:
        lines.append(current)
    return lines


def layout_rows(report: Report) -> list[RowLayout]:
    """Measure before painting; never overlap the photo or verification panel."""
    register_fonts()
    for size in (8.6, 8.2, 7.8):
        for step in (28, 26, 24, 22, 20):
            y, rows = 710.8, []
            leading = size * 1.24
            for item in report.table_fields:
                labels = _wrap(item.english_label, 111, size)
                values = _wrap(item.translated, 268 if y > 605 else 355, size)
                count = max(len(labels), len(values))
                rows.append(RowLayout(item, y, labels, values, size, leading))
                bottom = y - (count - 1) * leading - size * .3
                if bottom < 246:
                    break
                y -= max(step, count * leading + 8)
            else:
                return rows
    raise ValueError("所选信息超出模板单页可用空间，请缩短过长译文或取消显示部分字段。")


def export_pdf(report: Report, path: str | Path | None = None) -> bytes:
    if path and report.source_sha256 and Path(path).is_file():
        import hashlib
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() == report.source_sha256:
            raise ValueError("不能覆盖中文原始报告，请选择其他文件名。")
    errors = report.blockers()
    for item in report.output_fields:
        if re.search(r"[\u3400-\u9fff]", item.translated):
            errors.append(f"{item.label} 的英文译文仍包含中文")
        if len(item.translated) > 2000:
            errors.append(f"{item.label} 的译文过长")
    notes = [f for f in report.notes if f.shown]
    if len(notes) > 4:
        errors.append("此模板支持四条原文注意事项，当前报告的注意事项数量超出模板")
    if errors:
        raise ValueError("请完成校准后再导出：\n" + "\n".join(errors))
    register_fonts()
    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(ASSETS.joinpath("report_template.pdf").read_bytes())).pages[0])
    page = writer.pages[0]
    _clear_variable_text(page)
    overlay = io.BytesIO()
    can = canvas.Canvas(overlay, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
    can.setFillColorRGB(.6, .6, .6)
    dates = [f.english_label + ": " + f.translated for f in report.output_fields if f.key in {"renewal", "expiry"} and f.translated]
    _fit(can, "    ".join(dates), 180, 745.2, 357, label="报告日期")
    for row in layout_rows(report):
        for lines, x, width, color in ((row.labels, 60, 111, .29804),
                                        (row.values, 180, 268 if row.y > 605 else 355, 0)):
            can.setFillColorRGB(color, color, color)
            for index, line in enumerate(lines):
                _fit(can, line, x, row.y - index * row.leading, width, size=row.size, minimum=row.size, label=row.item.label)
    code = report.get("verification_code")
    if code and code.shown:
        can.setFillColorRGB(0, 0, 0)
        _fit(can, "Online Verification Code", 163.52985957, 202.27360934, 86, size=8)
        can.setFillColorRGB(0, 186/255, 199/255)
        _fit(can, code.translated, 252, 203.5, 280, size=10, font=MEDIUM, label="验证码")
    for data, x, y, width, height in ((report.qr, 75, 156, 68, 68), (report.photo, 460, 615, 75.6, 100.8)):
        if data:
            can.drawImage(ImageReader(io.BytesIO(data)), x, y, width, height)
    can.setFillColorRGB(0, 0, 0)
    for index, note in enumerate(notes):
        _fit(can, f"{index + 2}. {note.translated}", 61.6927308, (87 - 15 * index) * 1.000463,
             437, size=7, minimum=6, label=note.label)
    can.save()
    page.merge_page(PdfReader(io.BytesIO(overlay.getvalue())).pages[0])
    writer.add_metadata({"/Title": "Online Verification Report of Student Record - English Translation",
                         "/Author": "CHSI PDF Translator",
                         "/Subject": "Translation of a Chinese report; not an official CHSI-issued English report"})
    stream = io.BytesIO()
    writer.write(stream)
    content = stream.getvalue()
    if path:
        _atomic_write(Path(path), content)
    return content
