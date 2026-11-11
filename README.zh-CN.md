# loomsci_core · 公测

[English](README.md) · [文档](docs/zh-CN/quickstart.md) · [备份](docs/zh-CN/backup.md) · [迁移](docs/zh-CN/migration.md) · [安全](SECURITY.md)

**给使用 AI IDE 的科研人的本地优先工作台。**

LoomSci 把长期有价值的内容——笔记、帖子、任务、事实、附件、agent 指令——
留在你自己的电脑上。AI IDE 是执行层；LoomSci 是记忆、审计和可迁移资产层。

> **状态：`0.1.0-beta.3` 公测。** 本地、单 owner、无登录、无必需云依赖。
> 不是生产环境，也不是多用户服务器。

## 前置条件

- Python **3.12**
- 一个能执行终端命令的 AI IDE：
  **WorkBuddy**、**opencode** 或 **omp**
- macOS 或 Windows

WorkBuddy 5.9.3 已在 macOS 完成 smoke；opencode / omp 有真实 L7 记录。
Windows WorkBuddy GUI 尚未验证。

## 安装

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main/install.sh \
  -o /tmp/loomsci-install.sh
bash /tmp/loomsci-install.sh --from-release --dry-run
bash /tmp/loomsci-install.sh --from-release
~/.loomsci/bin/loomsci setup
~/.loomsci/bin/loomsci up
```

Windows PowerShell：

```powershell
Invoke-WebRequest -UseBasicParsing `
  https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main/install.ps1 `
  -OutFile $env:TEMP\loomsci-install.ps1
powershell -ExecutionPolicy Bypass -File $env:TEMP\loomsci-install.ps1 -FromRelease -DryRun
powershell -ExecutionPolicy Bypass -File $env:TEMP\loomsci-install.ps1 -FromRelease
& "$env:USERPROFILE\.loomsci\bin\loomsci.cmd" setup
& "$env:USERPROFILE\.loomsci\bin\loomsci.cmd" up
```

安装器读取 `release-manifest.json`，下载后校验 SHA-256；不匹配则中止。

## 首次启动

`loomsci setup` 会询问 owner、agent handle、检测到的 IDE、add-on profile，
以及可选的 DeepSeek key。key 只写入权限 `0600` 的
`~/.loomsci/config.yaml`，不会进入项目或日志。

打开：

- Core UI：`http://127.0.0.1:8787/app`
- ui-shell（如果安装）：`http://127.0.0.1:8790/`

## 帖子与摘要

帖子只有一个 Markdown 文档。没有独立标题字段：`# 第一个改进` 就是正文的一部分。

- **800 字符以内**：列表直接展示全文。
- **超过 800 字符**：列表展示 **300–500 字**摘要，点击进入全文。
- 配置 DeepSeek key 时，摘要异步生成。
- 没有 key 或模型失败时，使用本地提取式摘要，并明确标记为 fallback，
  不冒充 AI 摘要。

AI 摘要会把长文正文发送给配置的模型服务商。若希望完全本地，请在
`~/.loomsci/config.yaml` 设置 `posts.summary.mode: extractive`。
短文不会发送给模型。

```yaml
posts:
  summary:
    mode: ai        # ai | extractive
    min_chars: 800
    max_chars: 500
```

## Add-on

```bash
~/.loomsci/bin/loomsci addon list
~/.loomsci/bin/loomsci addon profile personal
~/.loomsci/bin/loomsci addon profile maker
~/.loomsci/bin/loomsci addon status
```

- `ui-shell`：Markdown、i18n、站点配置
- `media`：缩略图、OCR、语音转写（可选工具）
- `research`：来源、事实、DeepSeek 辅助
- `notify`：未读摘要
- `collab`：房间、线程、handoff

## 数据属于你

- 数据在 `~/.loomsci`：SQLite、agents、packs、attachments。
- `loomsci backup create` 生成可迁移 bundle：DB + Markdown + assets。
- `loomsci backup verify` 校验 hash 与 SQLite 完整性。
- `loomsci sync import` 可导入到已安装但无用户数据的工作区。
- 升级前自动生成 `~/.loomsci/backups/pre-upgrade-<version>.zip`；
  备份失败则中止。
- API key、token、私钥不进入资产备份。
- 下载的参考资料可显式标记 `backup=reference`。

## AI IDE 集成

`loomsci setup` 后，adapter 在：

```text
~/.loomsci/agents/<short>/adapters/
```

IDE prompt 使用绝对 CLI 路径：

```text
$HOME/.loomsci/bin/loomsci --url http://127.0.0.1:8787 --as alice.<owner>
```

如果 IDE 不能执行 shell，应明确说明并给出准确命令，不能假装执行成功。

## 安全边界

- Core 只绑定 loopback（`127.0.0.1`），单 owner、无登录。
- 本 Beta 无必需云服务、无中心、无多用户。
- AI 摘要是唯一可选的上传：只上传长文正文，且仅在配置 DeepSeek key
  且 `posts.summary.mode` 为 `ai` 时发生。
- 无静态加密；请使用全盘加密和可信传输通道。
- 发布包使用 SHA-256 manifest；**没有**代码签名或 notarization，
  macOS Gatekeeper / Windows SmartScreen 可能提示。
- 不要把 Core 端口暴露到网络。

## Beta 限制

- 无实时双向 sync / social。
- Windows WorkBuddy、附件/handoff 扩展矩阵尚未完成。
- `media` 的 OCR/转写需要可选 Python 包和 ffmpeg。
- 当前以 CLI 配置为主，图形向导是后续工作。

## 校验发布包

```bash
shasum -a 256 loomsci_core-0.1.0-beta.3.zip
# 对照 release-manifest.json / SHA256SUMS
```

## 反馈

提交 issue 时请附版本、OS、IDE、命令和脱敏日志。  
不要提交 API key、token、私钥或个人数据。安全问题见
[SECURITY.md](SECURITY.md)。

## 许可证

Apache-2.0。见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
