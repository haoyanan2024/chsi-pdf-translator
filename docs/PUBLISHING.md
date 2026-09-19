# GitHub 开源发布完整流程

首次发布基线：1.2.0。本文以 `haoyanan2024/chsi-pdf-translator` 为发布仓库。仓库尚未创建时，先按下方步骤创建；不要把文档中的下载链接当作已经发布成功的证明。

## 1. 发布结构与准备文件

源码、文档、模板和许可证放在 Git 仓库中；供普通用户下载的安装包放在 **Releases** 的 **Assets** 中。GitHub Releases 支持附加发行文件；每个附件须小于 2 GiB，本项目约 45 MiB 的安装器适合通过该功能分发。[GitHub 官方说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

准备这三个同版本文件：

```text
CHSI-Translator-Setup-1.2.0.exe
CHSI-Translator-Source-1.2.0.zip
SHA256SUMS.txt
```

仓库内容来自上述源码 ZIP 解压后的 `chsi-translator/` 内部，根目录应直接能看到 README.md、LICENSE、pyproject.toml、chsi_translator/、docs/ 和 .github/。不要把整个开发工作目录上传；也不要仅把源码 ZIP 当作仓库的唯一文件。

首次发行的安装器沿用已在本机验证的 1.2.0 二进制。此次公开准备增补了源码包中的文档、演示截图和构建工作流，没有改动应用核心。安装器内原有简短说明随原二进制保留，仓库和源码包提供完整新版文档。

## 2. 图形化发布方式：GitHub Desktop + 网页

这条路径适合不熟悉 Git 命令的维护者。安装 [GitHub Desktop](https://desktop.github.com/)，并在软件中通过浏览器登录 `haoyanan2024`。无需把 GitHub 密码或 Token 写到项目文件中。

### 2.1 创建空仓库

1. 浏览器登录 GitHub，打开 <https://github.com/new>。
2. Owner 选择 `haoyanan2024`，Repository name 填 `chsi-pdf-translator`。
3. Description 可填：`学信网中文学籍 PDF 自动翻译与校准工具，支持自适应字段和 Windows 安装版。`
4. 选择 **Public**。
5. 不勾选生成 README，不选择 .gitignore 或许可证模板：公开源码中已经具备这些文件。
6. 点击 **Create repository**。

### 2.2 上传实际源码

1. GitHub Desktop 选择 **File → Clone repository → URL**。
2. URL 填 `https://github.com/haoyanan2024/chsi-pdf-translator.git`；Local path 选一个新的空目录，例如 `D:\OpenSource\chsi-pdf-translator`。若提示空仓库，继续克隆即可。
3. 把公开源码 ZIP 解压后的 **内部全部文件和文件夹** 复制到该本地仓库中。不要额外套一层 `chsi-translator` 文件夹；不要覆盖或复制 `.git`。
4. 回到 Desktop 的 **Changes**，查看将要提交的文件。应包含 `.github`、文档、代码、模板、字体和许可证；不包含个人 PDF、草稿、照片、私有测试输出、EXE、虚拟环境或凭据。
5. Summary 填 `Initial public release 1.2.0`，点击 **Commit to main**。若需要设置作者信息，使用自己的 GitHub 显示名和 GitHub Settings → Emails 中提供的提交邮箱。
6. 点击 **Push origin**；随后在网页刷新仓库，应能浏览 Python 文件并看到完整 README。

若使用已经初始化的干净本地 Git 仓库，也可以通过 **File → Add local repository** 添加，然后 **Publish repository** 创建远端。选择公开发布时取消 **Keep this code private**。两个路径任选一个，不要重复创建同名仓库。[GitHub Desktop 官方步骤](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop)

### 2.3 发布安装包与源码包

1. 打开仓库主页，点击 **Releases → Create a new release**（已有发行版时为 **Draft a new release**）。
2. 选择或新建标签 `v1.2.0`，Target 选择刚上传源码的 `main`。
3. 标题填 `学籍报告英文助手 1.2.0`。
4. 将 [RELEASE_NOTES_1.2.0.md](RELEASE_NOTES_1.2.0.md) 的内容粘贴到描述中。
5. 在附件区域拖入安装器 EXE、源码 ZIP 和 `SHA256SUMS.txt`，等待三个文件全部上传完成。
6. 检查标签、目标分支和附件名，设置为最新正式版本，不勾选 pre-release。
7. 点击 **Publish release**。如果想先检查链接和附件，可先保存草稿；草稿对普通访问者不可见。

网页发布操作参照 [GitHub 管理 Releases 文档](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)。若仓库启用了不可变发行版，应在发布前上传所有附件；发布后需要修正二进制时，使用新版本号。

## 3. 命令行发布方式：Git + GitHub CLI

这是另一条完整路径，与上一节二选一。先安装 Git 和 [GitHub CLI](https://cli.github.com/)，重新打开 PowerShell，确认 `git --version` 与 `gh --version` 可用。

### 3.1 登录自己的 GitHub 账号

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth status
gh auth setup-git
```

按命令给出的提示在浏览器中登录并授权，确认账号是 `haoyanan2024`。额外的 workflow 权限用于推送本项目的 `.github/workflows` 文件。CLI 登录支持浏览器授权，通常使用系统凭据存储；不需要把 Token 粘贴进 README 或命令脚本。[官方登录说明](https://cli.github.com/manual/gh_auth_login)

### 3.2 初始化干净源码目录并提交

将下面路径改为自己解压出的公开源码目录。后面的 `git add .` 仅在该干净目录执行。

```powershell
Set-Location 'D:\OpenSource\chsi-pdf-translator'
git init -b main
git config user.name 'haoyanan2024'
# 从 GitHub Settings → Emails 复制自己的提交邮箱后替换下面示例
git config user.email 'YOUR_GITHUB_COMMIT_EMAIL'
git add .
git status --short
git diff --cached --stat
git commit -m 'Initial public release 1.2.0'
```

如果目录已经是 Git 仓库，跳过 `git init`，先确认处于 `main` 分支。不要原样使用邮箱占位符。仓库作者邮箱可以使用 GitHub 提供的 noreply 邮箱。

### 3.3 创建公开仓库并推送

尚未创建仓库时：

```powershell
gh repo create haoyanan2024/chsi-pdf-translator --public --source . --remote origin --push --description '学信网中文学籍 PDF 自动翻译与校准，支持自适应字段与 Windows 安装版'
```

`--source` 使用当前本地仓库，`--push` 推送提交。[官方 repo create 说明](https://cli.github.com/manual/gh_repo_create)

如果已在网页创建了空仓库，则使用下面命令，不再执行 `gh repo create`：

```powershell
git remote add origin https://github.com/haoyanan2024/chsi-pdf-translator.git
git push -u origin main
```

已有 origin 时先用 `git remote -v` 检查，不要盲目重复添加。远端若已有不同的提交历史，应先克隆并整合文件，不要用强制推送覆盖。

### 3.4 创建标签和发行版

把三个发行文件放到源码目录中的 `release/`；该目录已被 Git 忽略。确认 `SHA256SUMS.txt` 与当前文件匹配，再执行：

```powershell
git tag -a v1.2.0 -m 'CHSI PDF Translator 1.2.0'
git push origin v1.2.0

$releaseAssets = @(
  '.\release\CHSI-Translator-Setup-1.2.0.exe'
  '.\release\CHSI-Translator-Source-1.2.0.zip'
  '.\release\SHA256SUMS.txt'
)
gh release create v1.2.0 @releaseAssets --repo haoyanan2024/chsi-pdf-translator --verify-tag --title '学籍报告英文助手 1.2.0' --notes-file .\docs\RELEASE_NOTES_1.2.0.md --latest
```

`--verify-tag` 要求标签已存在于远端，避免错误地指向其他提交；`--notes-file` 从文件读取完整发布说明。[官方 release create 说明](https://cli.github.com/manual/gh_release_create)

若标签或 Release 已存在，不要重复执行创建命令或覆盖同名正式资产。先查看远端状态，已有正式版本的新修改应以新版本发布。

## 4. 发布后核对

- 在未登录的浏览器窗口打开仓库，确认是 Public，README、指南链接及演示截图正常显示。
- 打开 `https://github.com/haoyanan2024/chsi-pdf-translator/releases/latest`，确认能下载安装包、源码 ZIP 和哈希文件。
- 把下载后的 EXE/ZIP 重新计算 SHA-256，与同一 Release 中的清单比较。
- 解压源码 ZIP，确认有 docs、模板、字体、许可证和测试，无个人报告或草稿。
- 用下载下来的安装包测试安装、导入、字段勾选和导出；记录系统版本及结果。
- 在仓库 About 添加简介和主题，例如 `python`、`pdf`、`chsi`、`translation`、`windows`。

GitHub 自动生成的 `Source code (zip)`/`Source code (tar.gz)` 来自标签提交；我们额外上传的 `CHSI-Translator-Source-1.2.0.zip` 是白名单打包并带独立哈希的发行附件，两者文件打包形式不同属于正常现象。

## 5. GitHub Actions 的用途

仓库内 `.github/workflows/windows.yml` 在推送 `v*` 标签或手动 **Run workflow** 时构建 Windows 产物，执行测试和冻结程序自检，然后上传 `chsi-translator-windows` Artifact。

它只使用读取仓库的权限，不自动创建、修改或覆盖 Releases。首次公开发布应上传本地已验证的 EXE；如果未来选择 Actions 构建的 EXE，则下载同一次构建的整个产物，验证并使用其配套源码 ZIP 和哈希清单，不要混用不同构建的校验值。第一次上传之前，不能宣称 GitHub 上的构建已经通过。

## 6. 后续版本，例如 1.2.1

1. 修改功能并更新相关文档、测试和 CHANGELOG。
2. 将版本一致更新到 `chsi_translator/__init__.py`、`pyproject.toml`、`installer/setup.iss`、`installer/version_info.txt`、`scripts/package_source.py` 中的版本常量/文件名，以及 README 与发版说明中的版本引用。`version_info.txt` 的数字元组也需同步。
3. 按 [构建指南](DEVELOPMENT.md) 生成新安装器，完成测试、安装验证、PDF 视觉检查和卸载验证。
4. 运行源码打包，确认新的 `SHA256SUMS.txt` 对应本次新产物。白名单打包不是秘密扫描器，维护者仍应检查准备公开的内容。
5. 提交并推送代码，创建新标签 `v1.2.1`，为新版本单独发布 Release。
6. 保留旧版标签和附件，让下载者可以核对、回退；不对已发布版本悄悄替换二进制。

## 7. 常见发布错误

| 提示或现象 | 处理 |
| --- | --- |
| `gh` 或 `git` 未找到 | 安装对应工具并重新打开终端，或使用 Desktop 路线 |
| `Repository already exists` | 检查是否已经建好仓库，改为关联现有空仓库或克隆已有仓库 |
| `remote origin already exists` | 用 `git remote -v` 核对，不重复添加 |
| 推送 workflow 被拒绝 | 通过 `gh auth refresh -h github.com -s workflow` 补充授权后重试 |
| 身份不是 haoyanan2024 | 检查 `gh auth status`，在正确账号下完成浏览器授权 |
| `non-fast-forward` | 远端已有提交，先获取并整合；不要直接 force push |
| 发布页找不到 EXE | 检查附件是否传完；只有自动生成的 Source code 附件不代表安装包已上传 |
| 校验值不匹配 | 核对版本和构建来源，重新下载；发布前重新计算清单，不混用旧清单 |
| Actions 成功但没有 Release | 本项目工作流仅构建 Artifact；按本文上传并发布发行版 |

更多命令说明见 [GitHub 导入本地代码官方文档](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。
