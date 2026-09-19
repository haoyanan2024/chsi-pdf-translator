from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="中文学籍 PDF 自动翻译与校准")
    parser.add_argument("input", nargs="?", help="中文原始 PDF")
    parser.add_argument("--output", "-o", help="直接生成英文 PDF，不启动界面")
    parser.add_argument("--save-draft", help="同时保存校准草稿")
    parser.add_argument("--draft", help="从草稿生成英文 PDF，配合 --output")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--headless", action="store_true", help="自检时仅测试 Python 核心，无需图形桌面")
    parser.add_argument("--hide", action="append", default=[], metavar="KEY", help="隐藏字段，可重复使用，例如 --hide college --hide department")
    parser.add_argument("--show", action="append", default=[], metavar="KEY", help="显示字段，可重复使用")
    args = parser.parse_args()
    if args.self_test:
        try:
            from .selftest import run
            run(headless=args.headless)
            return 0
        except Exception:
            import json
            import os
            import traceback
            details = traceback.format_exc()
            if os.environ.get("CHSI_SELFTEST_OUTPUT"):
                Path(os.environ["CHSI_SELFTEST_OUTPUT"]).write_text(json.dumps({"status": "failed", "error": details}), encoding="utf-8")
            if sys.stderr:
                print(details, file=sys.stderr)
            return 1
    if args.output:
        from .export import export_pdf
        from .extract import extract_report
        from .model import Report
        if not args.input and not args.draft:
            parser.error("直接导出需要输入 PDF 或 --draft。")
        if args.input and Path(args.input).resolve() == Path(args.output).resolve():
            parser.error("输出文件不能覆盖中文原件。")
        try:
            report = Report.load(args.draft) if args.draft else extract_report(args.input)
            for keys, visible in ((args.hide, False), (args.show, True)):
                for key in keys:
                    item = report.get(key)
                    if item is None:
                        raise ValueError(f"不存在字段：{key}")
                    item.visible = visible
            if args.save_draft:
                report.save(args.save_draft)
            export_pdf(report, args.output)
            if sys.stdout:
                print("英文 PDF 已保存。")
            return 0
        except Exception as exc:
            if sys.stderr:
                print(str(exc), file=sys.stderr)
            return 1
    try:
        from .gui import launch
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("PySide6"):
            parser.error('图形界面需要安装 GUI 依赖：pip install ".[gui]"；服务器可使用 --output。')
        raise
    return launch(args.input)


if __name__ == "__main__":
    raise SystemExit(main())
