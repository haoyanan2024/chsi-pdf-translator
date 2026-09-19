from __future__ import annotations

import importlib.metadata as metadata
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "licenses"
PACKAGES = ["PySide6-Essentials", "shiboken6", "pdfplumber", "pdfminer.six", "pypdf", "pypdfium2",
            "reportlab", "Pillow", "pypinyin", "charset-normalizer", "cryptography", "cffi", "pycparser",
            "pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "packaging", "setuptools", "pywin32-ctypes"]


def main():
    TARGET.mkdir(exist_ok=True)
    versions = {"Python": sys.version}
    for name in PACKAGES:
        dist = metadata.distribution(name)
        versions[name] = dist.version
        for file in dist.files or []:
            lowered = str(file).lower()
            if ("licenses/" in lowered or Path(file).name.lower().startswith(("license", "copying", "notice"))) and ".." not in Path(file).parts:
                source = Path(dist.locate_file(file))
                if source.is_file():
                    destination = TARGET / name / str(file)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, TARGET / "Python-LICENSE.txt")
    (TARGET / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")
    # PyPI's PySide wheel omits LGPL/GPL texts; the release includes these upstream texts separately.
    for name in ("LGPL-3.0.txt", "GPL-3.0.txt"):
        path = TARGET / "Qt" / name
        if not path.exists() or path.stat().st_size < 5000:
            raise SystemExit(f"Missing {path}. Obtain the verbatim license text from https://www.gnu.org/licenses/ before packaging.")
    print("Third-party notices collected.")


if __name__ == "__main__":
    main()

