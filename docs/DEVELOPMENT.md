# Python 运行、开发与 Windows 构建

## 环境与目录

Python 最低版本为 3.10。已实测 Windows x64 / Python 3.12.14 和 Ubuntu 22.04.5 / Python 3.10.12。Windows 发布构建使用 Python 3.12 x64；其他环境可以运行 Python 核心，但不代表每个系统组合都已验证。

从 [仓库](https://github.com/haoyanan2024/chsi-pdf-translator) 克隆，或解压 Releases 中的 `CHSI-Translator-Source-1.2.0.zip`。进入能看到 `pyproject.toml` 和 `run_app.py` 的目录再执行以下命令。源码 ZIP 不含 Python 解释器、虚拟环境或 EXE。

## Windows：运行图形界面

先安装 Python 3.12 x64，在 PowerShell 中检查 `python --version`。创建环境并安装 GUI 依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[gui]"
.\.venv\Scripts\python.exe run_app.py
```

以上命令直接指定虚拟环境解释器，不需要激活环境，也不需要更改 PowerShell 全局执行策略。首次安装依赖需要联网，转换报告的默认流程离线。

如要使用本次 Windows 构建的锁定依赖组合，改为安装 `requirements-build.lock`。该文件用于 Windows 构建，不应当作为所有平台的通用锁文件。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.lock
```

## Linux：无桌面的核心运行

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[test]"
.venv/bin/python -m pytest -q
.venv/bin/python -m chsi_translator --self-test --headless
.venv/bin/python -m chsi_translator "中文报告.pdf" --output "English.pdf"
```

若系统缺少 `venv` 模块，先通过该系统的包管理器安装对应的 Python venv 支持。服务器只需核心依赖，不需要 Qt，也不需要图形桌面。需要 GUI 时另装 `.[gui]` 并提供可用桌面环境。

## 命令行

下面使用 `python` 代表已安装本项目的解释器。未激活虚拟环境时，应替换为前述完整解释器路径。

```powershell
# 无参数启动 GUI；提供文件时在 GUI 打开
python -m chsi_translator
python -m chsi_translator "中文报告.pdf"

# 自动提取、翻译、导出，同时保留校准草稿
python -m chsi_translator "中文报告.pdf" --output "English.pdf" --save-draft "review.chsi.json"

# 使用已校准草稿，不重复提取原件
python -m chsi_translator --draft "review.chsi.json" --output "English-reviewed.pdf"

# 隐藏分院与系所，剩余字段自动重排
python -m chsi_translator "中文报告.pdf" --output "English-compact.pdf" --hide college --hide department

# 在已填入学号的草稿中启用该项
python -m chsi_translator --draft "review.chsi.json" --output "English-with-id.pdf" --show student_id
```

`--output` 表示无 GUI 导出。`--hide` 和 `--show` 可重复指定；同一个键同时出现时，最终按显示处理。`--show` 只控制是否显示，不生成字段值。源文不存在的可选字段可为空，但姓名等必要字段选中时仍须满足校验。

若自动翻译遇到未收录术语，命令行会报错并以非零状态退出。可先生成草稿，再通过 GUI 校准；当指定 `--save-draft` 时，草稿保存先于 PDF 导出，即使待处理字段导致导出失败，草稿也可能已经生成。GUI 中“建议核对”的结果可导出，但应由用户复核。

### 字段键

| KEY | 中文字段 |
| --- | --- |
| `name` / `sex` / `birth` / `ethnicity` | 姓名 / 性别 / 出生日期 / 民族 |
| `institution` / `level` / `major` | 学校名称 / 层次 / 专业 |
| `duration` / `education` / `learning` | 学制 / 学历类别 / 学习形式 |
| `college` / `department` | 分院（学院、院系）/ 系所 |
| `class` / `student_id` | 班级 / 学号 |
| `start` / `status` / `graduation` | 入学日期 / 学籍状态 / 预计毕业日期 |
| `renewal` / `expiry` | 更新日期 / 失效日期（须原件中存在并被识别） |
| `verification_code` | 在线验证码 |
| `note_1`、`note_2` 等 | 已识别的各条注意事项 |

主表常用项会补齐为默认隐藏的可选项。日期、验证码或注意事项等键须以实际提取结果为准；指定不存在的键会报错。

## Python API 与草稿

```python
from chsi_translator.extract import extract_report
from chsi_translator.export import export_pdf
from chsi_translator.model import Report

report = extract_report("中文报告.pdf")
name = report.get("name")
if name is not None:
    name.translated = "ZHANG SAN"  # 示例：实际按本人证件核对
    name.status = "manual"        # 校准后同时更新状态

department = report.get("department")
if department is not None:
    department.visible = False

problems = report.blockers()
if problems:
    raise ValueError("；".join(problems))
report.save("review.chsi.json")
export_pdf(report, "English.pdf")

restored = Report.load("review.chsi.json")
restored.reset_visibility()       # 恢复原件字段选择，保留译文
export_pdf(restored, "English-source-fields.pdf")
```

`visible=None` 代表跟随原文是否存在，`True/False` 表示用户明确选择。`present` 记录原文是否有该项。`Report.table_fields` 为实际显示的主表行，`Report.output_fields` 还包括所选日期、验证码和注意事项。

草稿 schema 2 使用 UTF-8 JSON；图片和中文预览按 Base64 保存。旧 schema 1 会迁移到默认原件选择，旧附页开关被忽略。隐藏字段的内容仍在草稿中，不应把草稿当作匿名样例提交到仓库。

## 代码结构

| 文件 | 职责 |
| --- | --- |
| `chsi_translator/extract.py` | 中文文字层、坐标、照片和二维码提取 |
| `chsi_translator/translate.py` | 离线术语、日期、人名拼音、可选网络服务 |
| `chsi_translator/model.py` | 字段定义、显示选择、草稿、导出前校验 |
| `chsi_translator/export.py` | 保留模板背景，重绘并自适应排列主表 |
| `chsi_translator/gui.py` | 双语校准界面、后台任务、自动预览 |
| `chsi_translator/data/glossary.json` | 术语字典 |
| `tests/` / `chsi_translator/selftest.py` | 合成输入回归测试和端到端自检 |
| `scripts/` / `installer/` | 许可证收集、构建、源码打包、Inno Setup 配置 |

修改词库时保留原有 JSON 结构和 UTF-8 编码。修改模板前阅读 [模板来源记录](../chsi_translator/data/TEMPLATE_PROVENANCE.md)，不要直接替换成带示例个人信息的上游原文件。

## 测试与版式检查

```powershell
.\.venv\Scripts\python.exe -m pip install ".[gui,test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m chsi_translator --self-test
```

无桌面服务器使用 `--self-test --headless`。1.2.0 的 31 项测试和实测范围见 [VALIDATION.md](../VALIDATION.md)。网络翻译用模拟响应验证，GitHub 工作流在首次上传前未在 GitHub 上运行。

排版改动需额外检查默认字段、隐藏院系、多行长译文、最大字段数等输出。通过 Poppler `pdftoppm` 或 PDF 阅读器渲染并检查，确认背景花边完整、相邻行不重叠、照片和核验区未被遮挡。文档提取文本正确不足以证明视觉排版正确。

## 构建 Windows 安装包

在 Windows x64 上准备 Python 3.12 x64 和 [Inno Setup 6](https://jrsoftware.org/isinfo.php)。在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -InnoCompiler "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

此处执行策略仅作用于这次 PowerShell 进程。脚本会创建 `.venv`、安装锁定依赖、收集许可证、运行测试、构建 PyInstaller 程序、运行冻结自检、调用安装器编译器，最后打包源码和哈希。已经具备正确环境时可使用 `-SkipDependencies`，否则不要跳过依赖安装。

| 产物 | 用途 |
| --- | --- |
| `dist/CHSITranslator/` | 可运行的完整程序目录，EXE 依赖同目录文件 |
| `release/CHSI-Translator-Setup-1.2.0.exe` | 面向用户的安装器 |
| `release/CHSI-Translator-Source-1.2.0.zip` | 按白名单打包的公开源码与文档 |
| `release/SHA256SUMS.txt` | 此版本安装器与源码 ZIP 的 SHA-256 |

Qt 动态库保留为独立文件；构建脚本隔离 DLL 搜索路径，防止本机 Poppler、Conda 的同名 ICU 文件混入。不要删除该处理。构建日志可能需要保留以排错，但它们不属于公开源码包。

构建之后还应在本机安装测试、导入合成文档、修改显示选项、导出并卸载。PyInstaller 自检不等于完整安装验证；本次实测记录与未来每次新构建的结果应分别记录。

仅重新生成公开源码包与哈希：

```powershell
.\.venv\Scripts\python.exe scripts\package_source.py
```

脚本从白名单目录收集文件；只有经明确列入的模板、字体和合成截图允许作为二进制资源进入源码包。开发中不要把个人数据放进这些公开目录。
