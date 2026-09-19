from __future__ import annotations

import html
import json
import re
from datetime import datetime
from importlib.resources import files
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pypinyin import lazy_pinyin

from .model import Field, Report


GLOSSARY = json.loads(files("chsi_translator").joinpath("data/glossary.json").read_text("utf-8"))
CJK = re.compile(r"[\u3400-\u9fff]")
DATES = {"birth", "start", "graduation", "renewal", "expiry"}
ONLINE_KEYS = {"institution", "major", "department", "college"}
FIXED = {
    "sex": {"男": "Male", "女": "Female"},
    "level": {"博士研究生": "Postgraduate (Doctoral)", "硕士研究生": "Postgraduate (Master's)",
              "本科": "Undergraduate", "普通本科": "Undergraduate", "专科": "Junior College",
              "高职（专科）": "Higher Vocational (Junior College)", "第二学士学位": "Second Bachelor's Degree"},
    "education": {"普通高等教育": "Regular Higher Education", "成人高等教育": "Adult Higher Education",
                  "网络教育": "Online Education", "开放教育": "Open Education", "研究生": "Postgraduate Education"},
    "learning": {"全日制": "Full-time", "非全日制": "Part-time", "业余": "Spare-time",
                 "函授": "Correspondence", "脱产": "Full-time (Off-the-job)", "网络教育": "Online Learning"},
    "status": {"在籍（注册学籍）": "Registered", "在籍(注册学籍)": "Registered", "在籍": "Enrolled",
               "注册学籍": "Registered", "毕业": "Graduated", "结业": "Completed Studies",
               "休学": "On Leave", "退学": "Withdrawn", "保留学籍": "Student Status Retained",
               "保留入学资格": "Admission Eligibility Retained", "不在籍": "Not Enrolled"},
    "ethnicity": {"汉族": "Han", "汉": "Han", "满族": "Manchu", "回族": "Hui", "藏族": "Tibetan",
                  "蒙古族": "Mongol", "维吾尔族": "Uyghur", "壮族": "Zhuang", "苗族": "Miao",
                  "彝族": "Yi", "土家族": "Tujia", "朝鲜族": "Korean", "白族": "Bai",
                  "侗族": "Dong", "瑶族": "Yao", "布依族": "Bouyei", "哈萨克族": "Kazakh",
                  "傣族": "Dai", "黎族": "Li", "畲族": "She", "纳西族": "Naxi", "其他": "Other"},
}
COMPOUND_SURNAMES = {"欧阳", "司马", "上官", "诸葛", "夏侯", "东方", "皇甫", "尉迟", "公孙", "慕容", "令狐", "司徒", "司空"}
SURNAME_PINYIN = {"单": "SHAN", "解": "XIE", "仇": "QIU", "区": "OU", "查": "ZHA", "曾": "ZENG", "乐": "YUE"}
NOTE_RULES = [
    ("《学籍在线验证报告》是教育部学籍电子注册备案的查询结果。", "This report presents the results of a query of the Ministry of Education's electronic student registration records."),
    ("《教育部学籍在线验证报告》是教育部学籍电子注册备案的查询结果。", "This report presents the results of a query of the Ministry of Education's electronic student registration records."),
    ("报告内容如有修改，请以最新在线验证的内容为准。", "If the report is updated, the latest information available through online verification shall prevail."),
    ("未经学籍信息权属人同意，不得将报告用于违背权属人意愿之用途。", "This report must not be used against the wishes of the student record holder without their consent."),
    ("报告在线验证有效期由报告权属人设置（1~6个月），其在报告验证到期前可再次延长验证有效期。", "The report holder sets the online verification validity period (1 to 6 months) and may extend it before it expires."),
]


def translate_field(item: Field) -> None:
    source = item.source.strip()
    if not source:
        item.translated = ""
        item.status = "blank" if item.present else "missing"
        return
    item.hint = ""
    item.status = "auto"
    if item.key == "verification_code":
        item.translated = re.sub(r"\s+", "", source)
    elif item.key in DATES:
        parts = re.fullmatch(r"(\d{4})\s*[年/.-]\s*(\d{1,2})\s*[月/.-]\s*(\d{1,2})\s*日?", source)
        try:
            if not parts:
                raise ValueError("unrecognized date")
            date = datetime(*map(int, parts.groups()))
            month = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[date.month - 1]
            item.translated = f"{month}. {date.day:02d}, {date.year}"
        except ValueError:
            item.translated, item.status, item.hint = "", "pending", "日期格式无法识别，请对照原文校准。"
    elif item.key == "name" and CJK.search(source):
        chars = re.sub(r"\s+", "", source)
        split = 2 if chars[:2] in COMPOUND_SURNAMES else 1
        surname = SURNAME_PINYIN.get(chars[:split], "".join(lazy_pinyin(chars[:split])).upper())
        item.translated = surname + " " + "".join(lazy_pinyin(chars[split:])).upper()
        item.status, item.hint = "review", "自动拼音可能有多音字；请按护照英文姓名核对。"
    elif item.key == "duration":
        num = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*年", source)
        if num:
            value = num.group(1)
            item.translated = value + (" Year" if float(value) == 1 else " Years")
        else:
            item.translated, item.status = "", "pending"
    elif item.key.startswith("note_"):
        normalized = re.sub(r"\s+", "", source).replace("～", "~").rstrip("。.")
        item.translated = next((en for zh, en in NOTE_RULES if zh.rstrip("。.") == normalized), "")
        if not item.translated:
            item.status, item.hint = "pending", "原文注意事项与内置版本不同，请校准译文。"
    elif not CJK.search(source):
        item.translated = source
    elif source in FIXED.get(item.key, {}):
        item.translated = FIXED[item.key][source]
    elif source in GLOSSARY.get(item.key, {}):
        item.translated = GLOSSARY[item.key][source]
        item.status, item.hint = "review", "词库参考译名，可按学校官方名称校准。"
    else:
        item.translated, item.status = "", "pending"
        item.hint = "词库尚未收录，请手动校准" + ("，或使用可选联网翻译。" if item.key in ONLINE_KEYS else "。")


def translate_report(report: Report) -> Report:
    for item in report.all_fields:
        translate_field(item)
    return report


def online_candidates(report: Report) -> list[Field]:
    # Restrict network translation to institution/subject terminology; never identity fields.
    return [f for f in report.fields if f.shown and f.key in ONLINE_KEYS and f.status == "pending" and f.source]


def translate_online(term: str) -> str:
    """Optional MyMemory GET API. Called only after explicit UI opt-in."""
    if len(term.encode("utf-8")) > 500:
        raise ValueError("此术语超过联网接口的 500 字节上限，请手动翻译。")
    request = Request("https://api.mymemory.translated.net/get?" + urlencode({"q": term, "langpair": "zh-CN|en"}),
                      headers={"User-Agent": "CHSI-PDF-Translator/1.0"})
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read(1_000_000))
    if str(payload.get("responseStatus")) != "200":
        raise ValueError("翻译服务暂不可用或已达到免费配额，请稍后重试或手动校准。")
    result = html.unescape(payload.get("responseData", {}).get("translatedText", "")).strip()
    if not result or CJK.search(result) or len(result) > 1500:
        raise ValueError("服务未返回有效英文译文，请手动校准。")
    return result
