"""Small end-to-end check usable in a frozen Windows build. Only fictional data."""
from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


def make_fixture(path: Path, *, blank_college=True, wrapped=False, unknown_major=False, title=True):
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    can = canvas.Canvas(str(path), pagesize=(595, 842))
    can.setFont("STSong-Light", 18)
    can.drawString(178, 770, "教育部学籍在线验证报告" if title else "测试文档")
    can.setFont("STSong-Light", 10)
    can.drawString(225, 745, "更新日期：2026年09月18日")
    rows = [("姓名", "张三"), ("性别", "男"), ("出生日期", "2000年01月02日"), ("民族", "汉族"),
            ("学校名称", "北京大学"), ("层次", "硕士研究生"),
            ("专业", "未知测试专业" if unknown_major else "计算机科学与技术"), ("学制", "3 年"),
            ("学历类别", "普通高等教育"), ("学习形式", "全日制"), ("分院", "" if blank_college else "计算机学院"),
            ("系所", "软件研究所"), ("入学日期", "2025年09月01日"), ("学籍状态", "在籍（注册学籍）"),
            ("预计毕业日期", "2028年07月01日")]
    for i, (label, value) in enumerate(rows):
        y = 710 - i * 28
        can.drawString(60, y, label)
        if wrapped and label == "专业":
            can.drawString(179, y, "计算机科学")
            can.drawString(179, y - 13, "与技术")
        else:
            can.drawString(179, y, value)
    photo = Image.new("RGB", (160, 220), "#cedee7")
    draw = ImageDraw.Draw(photo)
    draw.ellipse((50, 24, 110, 84), fill="#ffffff")
    draw.rounded_rectangle((24, 102, 136, 245), radius=36, fill="#647f92")
    can.drawImage(ImageReader(photo), 455, 596, width=79.5, height=106)
    qr = Image.new("RGB", (147, 147), "white")
    draw = ImageDraw.Draw(qr)
    for x in range(7, 140, 7):
        for y in range(7, 140, 7):
            if (x * 3 + y * 7) % 5 < 2:
                draw.rectangle((x, y, x + 6, y + 6), fill="black")
    can.drawImage(ImageReader(qr), 77, 126, width=68, height=68)
    can.setFont("Helvetica", 12)
    can.drawString(215, 173, "DEMO0TEST12345678")
    can.setFont("STSong-Light", 10)
    can.drawString(164, 169, "在线验证码")
    can.drawString(164, 153, "验证报告在线查验网址：https://www.chsi.com.cn/xlcx/bgcx.jsp")
    can.drawString(62, 96, "注意事项：")
    can.setFont("STSong-Light", 8)
    notes = ["《学籍在线验证报告》是教育部学籍电子注册备案的查询结果。",
             "报告内容如有修改，请以最新在线验证的内容为准。",
             "未经学籍信息权属人同意，不得将报告用于违背权属人意愿之用途。",
             "报告在线验证有效期由报告权属人设置（1~6个月），其在报告验证到期前可再次延长验证有效期。"]
    for i, note in enumerate(notes):
        can.drawString(62, 80 - i * 13, str(i + 1) + "、" + note)
    can.save()


def run(headless=False):
    from pypdf import PdfReader
    from .extract import extract_report, render_page
    from .export import export_pdf
    from .model import Report

    with tempfile.TemporaryDirectory(prefix="chsi-selftest-") as directory:
        folder = Path(directory)
        make_fixture(folder / "中文测试.pdf")
        report = extract_report(folder / "中文测试.pdf")
        assert report.value("name") == "ZHANG SAN"
        assert report.get("college").source == ""
        assert report.photo and report.qr and report.preview
        assert len(report.notes) == 4 and not report.blockers()
        report.get("major").translated = "Computer Science (reviewed)"
        report.get("major").status = "manual"
        report.save(folder / "test.chsi.json")
        restored = Report.load(folder / "test.chsi.json")
        content = export_pdf(restored, folder / "English.pdf")
        assert "Computer Science (reviewed)" in PdfReader(io.BytesIO(content)).pages[0].extract_text()
        assert render_page(content)
        if not headless:
            _check_gui(restored)
    result = {"status": "passed", "checks": ["pdf-extraction", "offline-translation", "images", "draft-roundtrip", "pdf-export", "pdf-rendering"] + ([] if headless else ["gui-edit"])}
    if os.environ.get("CHSI_SELFTEST_OUTPUT"):
        Path(os.environ["CHSI_SELFTEST_OUTPUT"]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if __import__("sys").stdout:
        print(json.dumps(result))


def _check_gui(restored):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    from .gui import MainWindow
    app = QApplication.instance() or QApplication([])
    if os.name == "nt":
        QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc"))
    window = MainWindow()
    window.set_report(restored)
    window.ensurePolished()
    app.processEvents()
    assert window.table.rowCount() == len(restored.all_fields)
    from PySide6.QtCore import Qt
    import time
    def preview_ready():
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            app.processEvents()
            if not window.preview_timer.isActive() and window.worker is None:
                assert window.english_preview.pixmap is not None, window.english_preview.label.text()
                return
            time.sleep(.01)
        raise AssertionError("Automatic preview did not complete")
    preview_ready()
    window.table.item(0, 3).setText("ZHANG SAN TEST")
    assert restored.value("name") == "ZHANG SAN TEST"
    assert window.dirty
    index = next(i for i, f in enumerate(restored.all_fields) if f.key == "department")
    window.table.item(index, 0).setCheckState(Qt.CheckState.Unchecked)
    assert not restored.get("department").shown
    preview_ready()
    window.reset_fields_button.click()
    assert restored.get("department").shown
    assert restored.value("name") == "ZHANG SAN TEST"
    preview_ready()
    window.dirty = False
    window.close()
