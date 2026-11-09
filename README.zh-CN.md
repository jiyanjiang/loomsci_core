# loomsci_core

**你的个人 agent 的本地工作区。**
数据归你、无登录、可迁移，支持 macOS 与 Windows。

> **预览 seed。** 当前仓库只有规格、架构、路线图与文档骨架；
> 第一个可运行的 preview 版本尚未发布。这里的内容不应被理解为已交付功能。

[English](README.md) · [文档](docs/zh-CN/quickstart.md) · [架构](docs/zh-CN/architecture.md) · [源码映射](docs/zh-CN/source-map.md) · [路线图](docs/zh-CN/roadmap.md) · [安全](SECURITY.md) · [许可证](LICENSE)

## 为什么

- **归你。** 项目、帖子、任务、记忆、附件都在本机磁盘。
- **无账号。** 一个 owner、一个主 agent（默认 `alice`），不依赖云。
- **可迁移。** JSON + Markdown 全量导出；换 IDE、换机器不丢上下文。

AI IDE 是手和脚；`loomsci_core` 是记忆、协作总线和审计层。

## 在系统中的位置

```text
AI IDE agents（Codex / Pi / opencode / CodeBuddy）
                 │  CLI / HTTP
                 ▼
        loomsci_core host            默认单端口、只绑回环
        ├── 帖子 / 任务 / 租约
        ├── 记忆 / 事实 / 产物
        └── 本地边界 + 导出
```

## 快速开始（预览）

可运行安装器尚未发布。计划环境为 macOS 与 Windows 上的 Python 3.12。

macOS：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows（PowerShell）：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

预览阶段目前只声明 Flask。可用 `python -m cli.loomsci serve` 启动最小 host；
完整安装器仍在规划中。

## 状态

| 模块 | 状态 |
|---|---|
| 公共 seed / 文档 | 已有 |
| Core host + 本地 API | 最小 host + 帖子/任务总线（S1.4） |
| alice 基线 | 设计中 |
| macOS + Windows 安装 | 设计中 |
| 首个 preview 发布 | 待定 |

每次推送都会强制执行脱敏自检（API key、令牌、本机绝对路径、本地数据文件）。
见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

Apache-2.0。见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

## 安全

请勿用公开 issue 报告漏洞，见 [SECURITY.md](SECURITY.md)。
