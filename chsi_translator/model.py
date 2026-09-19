from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


# Key, source labels, English label. Explicit aliases keep label extraction auditable.
SPECS = [
    ("name", ("姓名",), "Name"),
    ("sex", ("性别",), "Sex"),
    ("birth", ("出生日期",), "Date of Birth"),
    ("ethnicity", ("民族",), "Ethnic Background"),
    ("institution", ("学校名称", "院校名称"), "Higher Education Institution"),
    ("level", ("层次", "学历层次", "培养层次"), "Education Level"),
    ("major", ("专业", "专业名称"), "Major"),
    ("duration", ("学制",), "Length of Program"),
    ("education", ("学历类别", "教育类型"), "Type of Education"),
    ("learning", ("学习形式",), "Form of Learning"),
    ("college", ("分院", "学院", "院系"), "College"),
    ("department", ("系所", "系（所）", "系(所)"), "Department / Institute"),
    ("class", ("班级",), "Class"),
    ("student_id", ("学号",), "Student Number"),
    ("start", ("入学日期",), "Start Date"),
    ("status", ("学籍状态",), "Status of Student Record"),
    ("graduation", ("预计毕业日期", "预计毕业时间"), "Anticipated Graduation Date"),
]
REQUIRED = {"name", "institution", "level", "major"}
STATUS_LABELS = {
    "auto": "自动翻译", "review": "建议核对", "pending": "待翻译",
    "manual": "已校准", "confirmed": "已核对", "blank": "原文空白",
    "missing": "未提取到", "online": "机器翻译·请核对",
}


@dataclass
class Field:
    key: str
    label: str
    english_label: str
    source: str
    translated: str = ""
    status: str = "pending"
    hint: str = ""
    present: bool = True
    visible: bool | None = None

    @property
    def shown(self) -> bool:
        return self.present if self.visible is None else self.visible


@dataclass
class Report:
    fields: list[Field] = field(default_factory=list)
    notes: list[Field] = field(default_factory=list)
    photo: bytes | None = None
    qr: bytes | None = None
    preview: bytes | None = None
    source_name: str = ""
    source_sha256: str = ""
    page_index: int = 0
    verification_url: str = "https://www.chsi.com.cn/xlcx/bgcx.jsp"
    warnings: list[str] = field(default_factory=list)

    def get(self, key: str) -> Field | None:
        return next((f for f in self.fields + self.notes if f.key == key), None)

    def value(self, key: str) -> str:
        item = self.get(key)
        return item.translated if item else ""

    @property
    def all_fields(self) -> list[Field]:
        return self.fields + self.notes

    @property
    def output_fields(self) -> list[Field]:
        return [f for f in self.all_fields if f.shown]

    @property
    def table_fields(self) -> list[Field]:
        return [f for f in self.fields if f.shown and f.key not in {"renewal", "expiry", "verification_code"}]

    def ensure_field_options(self):
        """Offer absent known fields without selecting or rearranging source rows."""
        rank = {spec[0]: i for i, spec in enumerate(SPECS)}
        for key, aliases, english_label in SPECS:
            if self.get(key):
                continue
            option = Field(key, aliases[0], english_label, "", status="blank", present=False,
                           hint="原文未显示此项；需要时勾选并填写英文，也可以留空。")
            index = next((i for i, f in enumerate(self.fields) if rank.get(f.key, len(SPECS)) > rank[key]), len(self.fields))
            self.fields.insert(index, option)

    def reset_visibility(self):
        for item in self.all_fields:
            item.visible = None

    def blockers(self) -> list[str]:
        errors = []
        for item in self.output_fields:
            if (item.source or item.key in REQUIRED) and not item.translated.strip():
                errors.append(f"{item.label} 尚未完成翻译")
            if item.status in {"pending", "missing"}:
                errors.append(f"{item.label} 需要校准")
        return list(dict.fromkeys(errors))

    def save(self, path: str | Path) -> None:
        obj = asdict(self)
        for key in ("photo", "qr", "preview"):
            obj[key] = base64.b64encode(obj[key]).decode("ascii") if obj[key] else None
        obj["schema_version"] = 2
        _atomic_write(Path(path), json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"))

    @classmethod
    def load(cls, path: str | Path) -> Report:
        path = Path(path)
        if path.stat().st_size > 30_000_000:
            raise ValueError("草稿文件过大。")
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.pop("schema_version", None) not in {1, 2}:
            raise ValueError("不支持此草稿版本。")
        # Old appendix flags no longer control output: default to source rows.
        obj.pop("include_appendix", None)
        for key in ("photo", "qr", "preview"):
            obj[key] = base64.b64decode(obj[key], validate=True) if obj.get(key) else None
        for key in ("fields", "notes"):
            obj[key] = [Field(**item) for item in obj[key]]
        report = cls(**obj)
        report.ensure_field_options()
        return report


def _atomic_write(path: Path, content: bytes) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
        tmp = Path(stream.name)
        stream.write(content)
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
