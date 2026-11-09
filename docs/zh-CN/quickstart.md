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

预览 seed 的 `requirements.txt` 故意留空。

## 计划中的首次运行（尚未实现）

```text
loomsci init          # 设置 owner 与默认 agent（alice）
loomsci serve         # 仅回环，默认端口 8787
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
