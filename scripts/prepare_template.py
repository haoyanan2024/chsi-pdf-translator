"""Prepare the pinned upstream template without its hidden example personal data.

Usage: python scripts/prepare_template.py path/to/upstream-template.pdf
The original source is never distributed in this project's releases.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

ROOT = Path(__file__).resolve().parents[1]
SOURCE_BLOB = "f37b674d58384cb4228a13efb3ab6d0299c01399"


def prepare(source: bytes) -> bytes:
    blob = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    if blob != SOURCE_BLOB:
        raise ValueError("Unexpected upstream template revision; review its content before importing.")
    reader = PdfReader(io.BytesIO(source))
    page = reader.pages[0]
    stream = page.get_contents()
    kept, suppress, removed_text, removed_images = [], False, 0, 0
    for operands, op in stream.operations:
        if op == b"BT":
            suppress = False
        if op == b"Tm":
            x, y = float(operands[4]), float(operands[5])
            suppress = (x > 170 and 370 < y < 755) or (x > 240 and 200 < y < 205)
        if suppress and op in {b"Tj", b"TJ", b"'", b'"'}:
            removed_text += 1
            continue
        if op == b"Do" and str(operands[0]) in {"/Im3", "/Im5"}:
            removed_images += 1
            continue
        kept.append((operands, op))
    if (removed_text, removed_images) != (15, 2):
        raise ValueError(f"Unexpected template structure: {removed_text} text blocks, {removed_images} images")
    stream.operations = kept
    page[NameObject("/Contents")] = stream
    for name in ("/Im3", "/Im5"):
        del page["/Resources"]["/XObject"][NameObject(name)]
    writer = PdfWriter()
    writer.add_page(page)
    writer.add_metadata({"/Title": "Student Record Template", "/Subject": "Upstream layout; hidden example personal data removed"})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


if __name__ == "__main__":
    content = prepare(Path(sys.argv[1]).read_bytes())
    target = ROOT / "chsi_translator/data/report_template.pdf"
    target.write_bytes(content)
    print(json.dumps({"template_sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}))
