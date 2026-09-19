# Third-party software

Application code is Apache-2.0. Dependencies keep their own licenses; see the
`licenses/` directory included in source and binary releases for verbatim notices.
Exact versions are in `requirements-build.lock` and `licenses/versions.json`.

| Component | Upstream | License |
| --- | --- | --- |
| PDF template and filling coordinates (modified) | https://github.com/muxiymmm/Online-Verification-Report-Translator20260714 | Apache-2.0 |
| Roboto Regular / Medium fonts (unmodified) | https://github.com/googlefonts/roboto-2 | Apache-2.0; Font data copyright Google 2011 |
| PySide6 Essentials / Shiboken6 / Qt Core, Gui, Widgets | https://doc.qt.io/qtforpython-6/ | LGPL-3.0; third-party notices also apply |
| pdfplumber | https://github.com/jsvine/pdfplumber | MIT |
| pdfminer.six | https://github.com/pdfminer/pdfminer.six | MIT |
| pypdf | https://github.com/py-pdf/pypdf | BSD-3-Clause |
| pypdfium2 / PDFium | https://github.com/pypdfium2-team/pypdfium2 | Apache-2.0 / BSD-3-Clause and bundled dependency notices |
| ReportLab | https://www.reportlab.com/ | BSD-style |
| Pillow | https://python-pillow.github.io/ | MIT-CMU / HPND and bundled notices |
| pypinyin | https://github.com/mozillazg/python-pinyin | MIT |
| CPython | https://www.python.org/ | PSF license |
| PyInstaller bootloader | https://pyinstaller.org/ | GPL with bootloader exception |

Qt/PySide/Shiboken are unmodified and dynamically linked. Their DLLs are left
separate under `_internal/`, and users may replace them with compatible builds.
Nothing in this project restricts reverse engineering for debugging modifications
to LGPL libraries. The application source and rebuild instructions are included.

Corresponding upstream sources for the distributed versions:

- PySide/Shiboken: https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/
- Qt: https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/
- PDFium binary build and source revision: the shipped `pypdfium2` version metadata and https://github.com/bblanchon/pdfium-binaries/releases
- CPython: https://www.python.org/downloads/source/

Optional network translation uses the MyMemory GET API. The application does not
bundle its service or submit translation-memory contributions. Its availability
and free quota are controlled by the provider:
https://mymemory.translated.net/doc/spec.php
