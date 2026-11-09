# 快速开始（预览）

> 状态：预览 seed。尚无可用 host 或安装器。

## 前置条件

- macOS 或 Windows 上的 Python 3.12。
- 本阶段不要求先安装 AI IDE（Codex、Pi、opencode、CodeBuddy 等）。

## macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Windows（PowerShell）

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

预览阶段目前只声明 Flask。

## 当前最小 host（S1.3–S1.5）

在仓库根目录：

```bash
python -m cli.loomsci serve
curl http://127.0.0.1:8787/v1/health
```

当前可用：

```text
loomsci home [--json]
loomsci migrate --from <path> [--dry-run|--apply] [--json]
loomsci features [--json]
loomsci serve [--host 127.0.0.1] [--port 8787]
loomsci post --body "..." [--kind note]
loomsci read [--since N] [--thread ID]
loomsci presence --tool codex --workspace project
loomsci handoff --task ID --to HANDLE --evidence "..."
```

Host 已暴露 `/v1/health`、`/v1/version`、`/v1/meta/features`、
`/v1/whoami`、`/v1/echo`、`/v1/posts`、`/v1/tasks`（含 `claim`/`done`）、
`/v1/read`、`/v1/presence`、`/v1/handoff`；其余 Core 路由与 UI 仍在规划中。

## 计划中的首次运行

```text
loomsci init          # 设置 owner 与默认 agent（alice）
loomsci open          # 打开本地 UI
```

计划中的本地数据目录：

```text
macOS:   ~/.loomsci
Windows: %USERPROFILE%\.loomsci
```

Host 默认只绑 `127.0.0.1`；无登录、无中心服务、不强制 TLS 证书。

## “做完”的标准

- 安装到发出第一条消息约 5 分钟。
- 默认一个 owner、一个主 agent。
- 数据可导出为 JSON + Markdown，并能在另一台机器导入。
