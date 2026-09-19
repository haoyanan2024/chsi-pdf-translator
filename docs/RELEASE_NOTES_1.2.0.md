# 学籍报告英文助手 1.2.0

将学信网直接下载的中文《教育部学籍在线验证报告》PDF 自动转换为可校准的英文翻译件，无需手填配置文件或截图照片。

## 下载哪个文件

- **普通 Windows 用户**：下载 `CHSI-Translator-Setup-1.2.0.exe`，双击安装，无需 Python。
- **开发者 / Linux 用户**：下载 `CHSI-Translator-Source-1.2.0.zip`，内含 Python 源码、测试、模板、字体、许可证和完整文档。
- **校验下载**：下载 `SHA256SUMS.txt`，用 PowerShell 的 `Get-FileHash -Algorithm SHA256 文件名` 比较对应哈希。

## 主要功能

- 自动提取原始文字、证件照、二维码和验证码，默认离线翻译。
- 双语对照、逐项英文校准、草稿保存及恢复。
- 默认显示中文原件所有已识别字段，原件中的空白行也保留。
- 分院、系所、班级、学号直接进入主表；逐行选择是否显示。
- 修改字段或译文后自动更新预览，主表行距和长文本自动适配，保留参考模板花边和底纹。
- Windows 安装版、Python 命令行和 API；可选的联网术语翻译。

## 使用步骤

安装 → 选择中文 PDF → 对照原件校准英文 → 按需勾选显示字段 → 检查英文预览 → 导出 PDF。

[完整操作指南](https://github.com/haoyanan2024/chsi-pdf-translator/blob/main/docs/USER_GUIDE.md) · [Python 与构建](https://github.com/haoyanan2024/chsi-pdf-translator/blob/main/docs/DEVELOPMENT.md) · [验证记录](https://github.com/haoyanan2024/chsi-pdf-translator/blob/main/VALIDATION.md)

## 支持与已知限制

支持带文字层的中文学籍报告 PDF；暂不支持扫描件、截图、学历/学位类报告和批量处理。词库不覆盖所有院校与专业，姓名拼音和正式英文名称应由用户复核。超出单页容量的内容会明确提示处理，不静默裁切。

目标系统为 Windows 10（1809+）/ 11 x64，安装器未签名。当前 Windows 主机和 Ubuntu 22.04.5 的 Python 核心测试通过，各 31 项；已验证本地安装、转换、自适应布局及卸载，未宣称所有系统与历史版式都兼容。

首次公开发布使用已实测的 1.2.0 安装器；源码包补充了完整公开文档和合成截图，应用核心不变。可选网络服务仅做模拟响应测试；GitHub Actions 是否通过以仓库中的实际运行记录为准。

## 隐私与许可

默认不上传 PDF 或个人信息。可选联网翻译会先列出待发送术语供确认；草稿含个人信息，不要公开上传。

输出为英文翻译件，不是学信网官方签发的英文报告。本项目与学信网、教育部无隶属关系。

代码采用 Apache-2.0，模板与 Roboto 字体源自 [muxiymmm 的参考项目](https://github.com/muxiymmm/Online-Verification-Report-Translator20260714)。保留第三方许可证和资源来源说明。
