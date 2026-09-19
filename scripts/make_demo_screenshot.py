"""Render the real GUI for public documentation, using fictional data only."""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main():
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from chsi_translator.extract import extract_report
    from chsi_translator.gui import MainWindow
    from chsi_translator.selftest import make_fixture

    app = QApplication.instance() or QApplication([])
    if os.name == "nt":
        QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc"))
    with tempfile.TemporaryDirectory(prefix="chsi-public-demo-") as temporary:
        fixture = Path(temporary) / "合成演示资料（虚构）.pdf"
        make_fixture(fixture)
        report = extract_report(fixture)
        window = MainWindow()
        window.resize(1600, 1080)
        window.set_report(report)
        window.tabs.setCurrentIndex(1)
        window.show()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            app.processEvents()
            if not window.preview_timer.isActive() and window.worker is None and window.english_preview.pixmap is not None:
                break
            time.sleep(.01)
        else:
            raise RuntimeError("Demo preview did not finish")
        app.processEvents()
        destination = ROOT / "docs/images/demo-main.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(destination)):
            raise RuntimeError("Could not save screenshot")
        window.dirty = False
        window.close()
        print("Saved public GUI screenshot using fictional data only.")


if __name__ == "__main__":
    main()
