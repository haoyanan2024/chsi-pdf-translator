from __future__ import annotations

import copy
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QToolBar, QVBoxLayout, QWidget,
)

from . import __version__
from .export import export_pdf
from .extract import extract_report, load_asset, render_page
from .model import Report, STATUS_LABELS
from .translate import online_candidates, translate_online


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, operation):
        super().__init__()
        self.operation = operation

    def run(self):
        try:
            self.done.emit(self.operation())
        except Exception as exc:
            self.failed.emit(str(exc))


class Preview(QScrollArea):
    def __init__(self, empty_text):
        super().__init__()
        self.setWidgetResizable(True)
        self.label = QLabel(empty_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(240)
        self.label.setStyleSheet("color:#6b7c87; padding:12px; background:#e9eff1;")
        self.setWidget(self.label)
        self.pixmap = None
        self.zoom = 1.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_image(self, data):
        pixmap = QPixmap()
        if data:
            pixmap.loadFromData(data)
        self.pixmap = pixmap if not pixmap.isNull() else None
        self.update_image()

    def set_message(self, text):
        self.pixmap = None
        self.setWidgetResizable(True)
        self.label.clear()
        self.label.setText(text)

    def update_image(self):
        if self.pixmap:
            scaled = self.pixmap.scaledToWidth(int(max(200, self.viewport().width() - 26) * self.zoom), Qt.TransformationMode.SmoothTransformation)
            self.setWidgetResizable(False)
            self.label.setPixmap(scaled)
            self.label.resize(scaled.width() + 26, scaled.height() + 26)
        else:
            self.label.clear()
            self.label.setText("暂无预览")

    def change_zoom(self, factor):
        self.zoom = max(1.0, min(3.0, self.zoom * factor)) if factor else 1.0
        self.update_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.report: Report | None = None
        self.worker: Worker | None = None
        self.dirty = False
        self.source_path: Path | None = None
        self.draft_path: Path | None = None
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.auto_preview)
        self.setWindowTitle(f"学籍报告英文助手  {__version__}")
        self.resize(1320, 900)
        self.setMinimumSize(1000, 680)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#f6f8fa; color:#193741; font-family:'Microsoft YaHei UI','Segoe UI'; font-size:13px; }
            QPushButton { background:white; border:1px solid #cfdbdf; border-radius:6px; padding:9px 13px; }
            QPushButton:hover { background:#edf5f5; border-color:#14858a; }
            QPushButton:disabled { color:#9daab1; background:#eef1f3; }
            QPushButton#primary { background:#137e83; color:white; border:1px solid #137e83; font-weight:600; }
            QPushButton#primary:disabled { background:#93b8ba; border-color:#93b8ba; }
            QTableWidget { background:white; border:1px solid #dde5e8; gridline-color:#e6ecef; selection-background-color:#deeeee; selection-color:#193741; }
            QHeaderView::section { background:#edf3f5; border:0; border-bottom:1px solid #d4e0e4; padding:9px; font-weight:600; }
            QTabWidget::pane { border:1px solid #dde5e8; }
            QTabBar::tab { padding:9px 20px; background:#e9eff2; }
            QTabBar::tab:selected { background:white; color:#087c81; }
            QToolBar { border:0; spacing:8px; padding:4px; }
        """)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 14)
        title = QLabel("学籍报告英文助手")
        title.setStyleSheet("font-size:25px; font-weight:700;")
        layout.addWidget(title)
        layout.addWidget(QLabel("导入中文 PDF，自动提取文字、照片和二维码。对照校准后，导出英文翻译件。"))
        actions = QHBoxLayout()
        self.open_button = self.button("选择中文 PDF", self.choose_pdf, primary=True)
        self.draft_button = self.button("打开草稿", self.choose_draft)
        self.save_button = self.button("保存草稿", self.save_draft)
        self.online_button = self.button("联网翻译待处理术语", self.online_translate)
        self.preview_button = self.button("刷新英文预览", self.preview_english)
        self.export_button = self.button("导出英文 PDF", self.export, primary=True)
        for button in (self.open_button, self.draft_button, self.save_button, self.online_button, self.preview_button, self.export_button):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.summary = QLabel("① 选择或拖入 PDF　 →　 ② 校准英文　 →　 ③ 导出 PDF")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("padding:10px; background:#eaf3f3; border-radius:6px; color:#17666c;")
        layout.addWidget(self.summary)
        display_options = QHBoxLayout()
        display_options.addWidget(QLabel("勾选“显示”选择 PDF 字段，主表自动排版；默认与中文原件一致，包含原文空白项。"))
        display_options.addStretch()
        self.reset_fields_button = self.button("恢复原文字段", self.reset_fields)
        display_options.addWidget(self.reset_fields_button)
        layout.addLayout(display_options)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        self.tabs = QTabWidget()
        self.source_preview = Preview("将学信网直接下载的中文 PDF 拖到这里\n\n无需填写配置文件，无需手动裁剪照片。")
        self.english_preview = Preview("校准后点击“刷新英文预览”")
        self.tabs.addTab(self.source_preview, "中文原件")
        self.tabs.addTab(self.english_preview, "英文预览")
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        zoom_buttons = QHBoxLayout()
        for label, factor in [("放大", 1.25), ("缩小", .8), ("适合宽度", 0)]:
            zoom_buttons.addWidget(self.button(label, lambda checked=False, f=factor: self.tabs.currentWidget().change_zoom(f)))
        zoom_buttons.addStretch()
        left_layout.addLayout(zoom_buttons)
        left_layout.addWidget(self.tabs)
        splitter.addWidget(left)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.addWidget(QLabel("勾选控制显示，双击英文即可校准；修改后自动刷新英文预览。"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["显示", "字段", "中文原文", "英文译文（可编辑）", "状态"])
        self.table.verticalHeader().hide()
        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self.item_changed)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        right_layout.addWidget(self.table, 1)
        self.hint = QLabel("姓名拼音请按护照核对；学校和专业可使用官方英文译名。")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color:#697d87; padding:5px;")
        right_layout.addWidget(self.hint)
        extras = QHBoxLayout()
        self.confirm_button = self.button("标记选中项已核对", self.confirm_selected)
        self.photo_button = self.button("检查 / 更换照片", lambda: self.asset_dialog("photo"))
        self.qr_button = self.button("检查 / 更换二维码", lambda: self.asset_dialog("qr"))
        for button in (self.confirm_button, self.photo_button, self.qr_button):
            extras.addWidget(button)
        right_layout.addLayout(extras)
        splitter.addWidget(right)
        splitter.setSizes([410, 860])
        footer = QHBoxLayout()
        self.privacy = QLabel("默认离线处理 · 资料保留在本机 · 输出为英文翻译件")
        self.privacy.setStyleSheet("color:#6b7d85; font-size:12px;")
        footer.addWidget(self.privacy)
        footer.addStretch()
        about = self.button("使用说明", self.about)
        footer.addWidget(about)
        layout.addLayout(footer)
        self.statusBar().showMessage("准备就绪")
        for key, callback in [("Ctrl+O", self.choose_pdf), ("Ctrl+S", self.save_draft), ("Ctrl+E", self.export)]:
            action = QAction(self)
            action.setShortcut(key)
            action.triggered.connect(callback)
            self.addAction(action)
        self.refresh_controls()

    @staticmethod
    def button(label, callback, primary=False):
        button = QPushButton(label)
        button.clicked.connect(callback)
        if primary:
            button.setObjectName("primary")
        return button

    def refresh_controls(self):
        busy = self.worker is not None
        loaded = self.report is not None
        for button in (self.save_button, self.preview_button, self.export_button, self.confirm_button, self.photo_button, self.qr_button):
            button.setEnabled(loaded and not busy)
        self.online_button.setEnabled(loaded and not busy and bool(online_candidates(self.report)))
        self.open_button.setEnabled(not busy)
        self.draft_button.setEnabled(not busy)
        self.table.setEnabled(not busy)
        self.reset_fields_button.setEnabled(loaded and not busy)
        if loaded:
            pending = sum(f.status in {"pending", "missing"} for f in self.report.output_fields)
            review = sum(f.status in {"review", "online"} for f in self.report.output_fields)
            assets = f"照片 {'已提取' if self.report.photo else '未提取'} · 二维码 {'已提取' if self.report.qr else '未提取'}"
            self.summary.setText(f"{self.report.source_name}  |  主表显示 {len(self.report.table_fields)} 项  |  {assets}\n所选字段待翻译 {pending} 项 · 建议核对 {review} 项" +
                                 ("\n" + "；".join(self.report.warnings) if self.report.warnings else ""))

    def run_job(self, operation, done, message, failed=None):
        if self.worker:
            return
        self.statusBar().showMessage(message)
        worker = Worker(operation)
        self.worker = worker
        worker.done.connect(done)
        worker.failed.connect(failed or (lambda text: QMessageBox.warning(self, "操作未完成", text)))
        worker.finished.connect(self.job_finished)
        worker.finished.connect(worker.deleteLater)
        self.refresh_controls()
        worker.start()

    def job_finished(self):
        self.worker = None
        self.refresh_controls()
        self.statusBar().showMessage("准备就绪")

    def discard_ok(self):
        if self.worker:
            return False
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, "保存校准结果", "有尚未保存的校准结果，是否先保存草稿？",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save_draft()
        return answer == QMessageBox.StandardButton.Discard

    def choose_pdf(self):
        if not self.discard_ok():
            return
        path, _ = QFileDialog.getOpenFileName(self, "选择学信网中文学籍报告", "", "PDF 文件 (*.pdf)")
        if path:
            self.load_pdf(path)

    def load_pdf(self, path):
        def done(report):
            self.source_path = Path(path).resolve()
            self.draft_path = None
            self.set_report(report)
        self.run_job(lambda: extract_report(path), done, "正在本地提取 PDF 并翻译，请稍候…")

    def set_report(self, report):
        self.preview_timer.stop()
        report.ensure_field_options()
        self.report = report
        self.dirty = False
        self.source_preview.set_image(report.preview)
        self.english_preview.set_image(None)
        self.tabs.setCurrentIndex(0)
        self.populate()
        self.refresh_controls()
        self.schedule_preview()

    def populate(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.report.all_fields))
        for row, item in enumerate(self.report.all_fields):
            values = ["", item.label, item.source or ("（原文空白）" if item.present else "（原文未显示 / 未提取）"), item.translated, STATUS_LABELS.get(item.status, item.status)]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(item.hint or item.source)
                if column != 3:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column == 0:
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    cell.setCheckState(Qt.CheckState.Checked if item.shown else Qt.CheckState.Unchecked)
                    cell.setToolTip("勾选后写入 PDF；不勾选时标签和内容均不显示。")
                if not item.shown:
                    cell.setForeground(QColor("#8b969c"))
                elif column == 4:
                    cell.setForeground(QColor("#ad5c11" if item.status in {"pending", "review", "missing", "online"} else "#197970"))
                self.table.setItem(row, column, cell)
        self.table.resizeRowsToContents()
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, max(39, self.table.rowHeight(row)))
        self.table.blockSignals(False)

    def reset_fields(self):
        if self.report:
            self.report.reset_visibility()
            self.dirty = True
            self.populate()
            self.refresh_controls()
            self.tabs.setCurrentIndex(1)
            self.schedule_preview()

    def schedule_preview(self):
        self.english_preview.set_message("正在更新英文预览…")
        self.preview_timer.start(400)

    def auto_preview(self):
        if not self.report:
            return
        if self.worker:
            self.preview_timer.start(200)
            return
        errors = self.report.blockers()
        if errors:
            self.english_preview.set_message("请先校准已勾选的字段：\n" + "\n".join(errors))
            return
        snapshot = copy.deepcopy(self.report)
        self.run_job(lambda: render_page(export_pdf(snapshot)), self.english_preview.set_image,
                     "正在更新英文预览…", failed=lambda text: self.english_preview.set_message(text))

    def item_changed(self, cell):
        if not self.report or cell.column() not in {0, 3}:
            return
        item = self.report.all_fields[cell.row()]
        if cell.column() == 0:
            item.visible = cell.checkState() == Qt.CheckState.Checked
            self.tabs.setCurrentIndex(1)
        else:
            item.translated = cell.text().strip()
            item.status = "manual" if item.translated else ("blank" if not item.source else "pending")
        self.dirty = True
        self.table.blockSignals(True)
        self.table.item(cell.row(), 4).setText(STATUS_LABELS[item.status])
        for column in range(5):
            color = "#8b969c" if not item.shown else ("#ad5c11" if column == 4 and item.status in {"pending", "review", "missing", "online"} else "#193741")
            self.table.item(cell.row(), column).setForeground(QColor(color))
        self.table.blockSignals(False)
        self.schedule_preview()
        self.table.resizeRowToContents(cell.row())
        self.refresh_controls()

    def selection_changed(self):
        row = self.table.currentRow()
        if self.report and row >= 0:
            self.hint.setText(self.report.all_fields[row].hint or "可直接修改英文译文，中文原文保持不变。")

    def confirm_selected(self):
        rows = {index.row() for index in self.table.selectedIndexes()}
        for row in rows:
            item = self.report.all_fields[row]
            if item.translated:
                item.status = "confirmed"
                self.dirty = True
        self.populate()
        self.refresh_controls()

    def choose_draft(self):
        if not self.discard_ok():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开校准草稿", "", "报告草稿 (*.chsi.json)")
        if path:
            try:
                report = Report.load(path)
                self.source_path = None
                self.draft_path = Path(path)
                self.set_report(report)
            except Exception as exc:
                QMessageBox.warning(self, "无法打开草稿", str(exc))

    def save_draft(self):
        if not self.report or self.worker:
            return False
        suggestion = str(self.draft_path or Path.home() / "Documents" / (Path(self.report.source_name).stem + ".chsi.json"))
        path, _ = QFileDialog.getSaveFileName(self, "保存校准草稿（包含个人资料，请妥善保存）", suggestion, "报告草稿 (*.chsi.json)")
        if not path:
            return False
        if not path.lower().endswith(".chsi.json"):
            path += ".chsi.json"
        try:
            self.report.save(path)
            self.draft_path = Path(path)
            self.dirty = False
            self.statusBar().showMessage("草稿已保存", 6000)
            return True
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return False

    def preview_english(self):
        if not self.report:
            return
        self.preview_timer.stop()
        snapshot = copy.deepcopy(self.report)
        def done(data):
            self.english_preview.set_image(data)
            self.tabs.setCurrentIndex(1)
        self.run_job(lambda: render_page(export_pdf(snapshot)), done, "正在生成英文预览…")

    def export(self):
        if not self.report or self.worker:
            return
        errors = self.report.blockers()
        if errors:
            QMessageBox.warning(self, "请先校准待处理项", "\n".join(errors))
            return
        missing_assets = [label for label, data in [("证件照", self.report.photo), ("二维码", self.report.qr)] if not data]
        if missing_assets:
            if QMessageBox.question(self, "图片尚未提取", "、".join(missing_assets) + "尚未提取。是否仍导出？") != QMessageBox.StandardButton.Yes:
                return
        suggestion = str(Path.home() / "Documents" / (Path(self.report.source_name).stem + "_English.pdf"))
        path, _ = QFileDialog.getSaveFileName(self, "导出英文 PDF", suggestion, "PDF 文件 (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        if self.source_path and Path(path).resolve() == self.source_path:
            QMessageBox.warning(self, "请保留中文原件", "请选择不同文件名，避免覆盖中文原始报告。")
            return
        snapshot = copy.deepcopy(self.report)
        def done(_):
            box = QMessageBox(self)
            box.setWindowTitle("导出完成")
            box.setText("英文 PDF 已保存：\n" + path)
            open_button = box.addButton("打开 PDF", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("完成", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == open_button:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        self.run_job(lambda: export_pdf(snapshot, path), done, "正在导出英文 PDF…")

    def online_translate(self):
        candidates = online_candidates(self.report)
        if not candidates:
            return
        terms = "\n".join("• " + f.source for f in candidates)
        message = "仅将以下术语发送至 MyMemory 免费翻译服务（第三方，有使用配额）：\n\n" + terms + "\n\n不发送 PDF、姓名、照片或验证码。是否继续？"
        if QMessageBox.question(self, "可选联网翻译", message) != QMessageBox.StandardButton.Yes:
            return
        def operation():
            results, failures = {}, []
            for item in candidates:
                try:
                    results[item.key] = translate_online(item.source)
                except Exception as exc:
                    failures.append(item.label + "：" + str(exc))
            return results, failures
        def done(result):
            results, failures = result
            for key, value in results.items():
                item = self.report.get(key)
                item.translated, item.status = value, "online"
                item.hint = "第三方机器译文，请核对后使用。"
            self.dirty = True
            self.populate()
            self.schedule_preview()
            if failures:
                QMessageBox.warning(self, "部分术语未翻译", "\n".join(failures))
        self.run_job(operation, done, "正在联网翻译所选术语…")

    def asset_dialog(self, key):
        from PySide6.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("证件照" if key == "photo" else "二维码")
        layout = QVBoxLayout(dialog)
        preview = Preview("未提取到图片")
        preview.setMinimumSize(300, 340)
        preview.set_image(getattr(self.report, key))
        layout.addWidget(preview)
        def replace():
            path, _ = QFileDialog.getOpenFileName(dialog, "选择替换图片", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
            if path:
                try:
                    setattr(self.report, key, load_asset(path))
                    self.dirty = True
                    preview.set_image(getattr(self.report, key))
                    self.schedule_preview()
                    self.report.warnings = [w for w in self.report.warnings if ("证件照" if key == "photo" else "二维码") not in w]
                    self.refresh_controls()
                except Exception as exc:
                    QMessageBox.warning(dialog, "图片读取失败", str(exc))
        layout.addWidget(self.button("选择替换图片", replace))
        layout.addWidget(self.button("完成", dialog.accept))
        dialog.exec()

    def about(self):
        QMessageBox.information(self, "使用说明", "1. 选择或拖入学信网直接下载的中文《教育部学籍在线验证报告》PDF。\n"
            "2. 文字、照片、二维码自动提取；双击英文单元格即可修改。\n"
            "3. 核对护照姓名、学校和专业译名；点击刷新英文预览或导出 PDF。\n"
            "4. 保存草稿可保留全部校准结果和图片，下次直接打开。\n\n"
            "默认不联网，不收集资料；可选联网功能仅发送界面列出的学校、专业或院系术语。\n"
            "当前支持带文字层的中文学籍报告，不支持扫描件和学历/学位报告。\n"
            "使用参考项目的花边、底纹和 Roboto 字体，主表自动安排所选字段。\n"
            "分院、系所等直接插入主表；默认显示原文所有字段（含空白项）。\n"
            "可逐项勾选显示，也可恢复原文字段；选择及译文修改后自动刷新预览。\n"
            "长译文自动换行并调整行距；过量内容超出单页时会提示，不截断信息。\n"
            "日期按原文转换，没有失效日期时不推算；注意事项按原文翻译。\n"
            "输出是翻译件，核验码对应中文原件，不构成学信网官方英文报告。\n\n"
            f"版本 {__version__} · Apache-2.0 · 参考项目 muxiymmm/Online-Verification-Report-Translator20260714")

    def dragEnterEvent(self, event):
        if not self.worker and event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                event.acceptProposedAction()

    def dropEvent(self, event):
        if self.discard_ok():
            self.load_pdf(event.mimeData().urls()[0].toLocalFile())
            event.acceptProposedAction()

    def closeEvent(self, event):
        if self.worker:
            QMessageBox.information(self, "正在处理", "请等待当前操作完成后关闭。")
            event.ignore()
        elif self.discard_ok():
            self.preview_timer.stop()
            event.accept()
        else:
            event.ignore()


def launch(path=None):
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("学籍报告英文助手")
    app.setOrganizationName("CHSI PDF Translator")
    window = MainWindow()
    window.show()
    if path:
        QTimer.singleShot(100, lambda: window.load_pdf(path))
    return app.exec()
