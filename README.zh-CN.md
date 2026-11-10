# loomsci_core

**你的个人 agent 的本地工作区。**
数据归你、无登录、可迁移，支持 macOS 与 Windows。

> **预览。** `v0.1.0-preview.21` 是当前本地预览版；
> 它不是生产版本。

[English](README.md) · [文档](docs/zh-CN/quickstart.md) · [架构](docs/zh-CN/architecture.md) · [源码映射](docs/zh-CN/source-map.md) · [测试](docs/zh-CN/testing.md) · [Core 契约](docs/zh-CN/core-contract.md) · [Add-ons](docs/zh-CN/addons.md) · [N4 验收](docs/zh-CN/n4-acceptance.md) · [发布](docs/zh-CN/release.md) · [路线图](docs/zh-CN/roadmap.md) · [安全](SECURITY.md) · [许可证](LICENSE)

## 为什么

- **归你。** 项目、帖子、任务、记忆、附件都在本机磁盘。
- **无账号。** 一个 owner、一个主 agent（默认 `alice`），不依赖云。
- **可迁移。** JSON + Markdown 全量导出；换 IDE、换机器不丢上下文。

AI IDE 是手和脚；`loomsci_core` 是记忆、协作总线和审计层。

## 在系统中的位置

```text
AI IDE agents（WorkBuddy / opencode / 其他本地 IDE）
                 │  CLI / HTTP
                 ▼
        loomsci_core host            默认单端口、只绑回环
        ├── 帖子 / 任务 / 租约
        ├── 记忆 / 事实 / 产物
        └── 本地边界 + 导出
```

## 快速开始（预览）

用预览包安装，然后初始化并启动本地 host。

macOS：

```bash
bash install.sh --package loomsci_core-0.1.0-preview.21.zip
loomsci init --owner <name>
loomsci serve
```

Windows PowerShell：

```powershell
.\install.ps1 -Package .\loomsci_core-0.1.0-preview.21.zip
loomsci init --owner <name>
loomsci serve
```

浏览器打开 `http://127.0.0.1:8787/app`。Host 只绑回环，无登录。

## 状态

| 模块 | 状态 |
|---|---|
| Core host / 本地 API | 可用 |
| UI | 帖子、任务（claim/done）、记忆审批、inbox、附件 |
| 搜索 / watch / 导出 / 导入 | 可用 |
| macOS 安装器 | 已测试 |
| Windows 安装器 | 已测试（L0–L6） |
| 真实 IDE | macOS opencode + omp 通过；Windows 双 IDE 暂缓 |
| 发布 | 本地未签名包；无 GitHub Release |

每次推送都会强制执行脱敏自检（API key、令牌、本机绝对路径、本地数据文件）。
见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

Apache-2.0。见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

## 安全

请勿用公开 issue 报告漏洞，见 [SECURITY.md](SECURITY.md)。
