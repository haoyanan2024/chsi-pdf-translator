"""Allowlist packaging: private reports can never enter the public source archive."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ("chsi_translator", "tests", "scripts", "installer", "licenses", ".github", "docs")
FILES = ("README.md", "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "pyproject.toml", ".gitignore",
         "requirements-build.lock", "CHSITranslator.spec", "run_app.py", "VALIDATION.md",
         "CHANGELOG.md", "CONTRIBUTING.md")
ALLOWED = {".py", ".json", ".txt", ".md", ".ps1", ".iss", ".isl", ".yml", ".yaml", ".ijg"}
ASSETS = {"chsi_translator/data/report_template.pdf", "chsi_translator/data/fonts/Roboto-Regular.ttf",
          "chsi_translator/data/fonts/Roboto-Medium.ttf", "docs/images/demo-main.png"}


def main():
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    archive = output / "CHSI-Translator-Source-1.2.0.zip"
    paths = [ROOT / name for name in FILES if (ROOT / name).is_file()]
    for directory in DIRS:
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if directory == "licenses" or path.suffix.lower() in ALLOWED or path.relative_to(ROOT).as_posix() in ASSETS:
                paths.append(path)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(set(paths)):
            z.write(path, Path("chsi-translator") / path.relative_to(ROOT))
    checksums = []
    for path in sorted(output.iterdir()):
        if path.suffix.lower() in {".zip", ".exe"} and "1.2.0" in path.name:
            checksums.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name)
    (output / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="ascii")
    print(f"Packaged {len(paths)} public source files.")


if __name__ == "__main__":
    main()

