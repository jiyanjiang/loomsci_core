# 路线图 · Core + Apps

> 不承诺日期。只有验收通过，阶段才算完成。`0.1.0-beta.28` 是旧实现；本路线图描述 Core + Apps 产品线，不是继续堆旧功能。

## 定位

```text
LoomSci Core = 面向 AI 原生技术用户的最小、稳定、本地优先运行时
LoomSci App  = 建立在 Core 上的垂直产品
TAA          = 先锋实验平台，不是 Core 代码库
```

- 主要用户：AI 原生研究者、独立开发者、AI Maker、小型技术团队。
- 不是大众笔记软件，不是通用 AI 工作空间，不是 TAA 复刻。
- Python 3.12 是可接受运行时；安装器用 `uv` 自动准备，不要求用户手动装 Python。
- 原生二进制不是 M0 阻断项。
- 不强制注册；付费/云能力属于 App。

## M0 · 架构冻结

**目标：** 把 Core/App 契约从“声明”变成可执行协议。

交付物：

- Process contract：App 启动、token 传递、health、退出码、stdout/stderr、崩溃重启。
- Runtime contract：Python 3.12 + uv 独立运行时 + venv 布局 + 离线安装。
- Signing/trust：ed25519 密钥层级、公钥分发、轮换、撤销、离线校验。
- 数据分层：Core `items` 与 App 自有表；Report/Project 映射。
- 备份/恢复语义：范围、格式、覆盖/合并、版本不匹配、失败行为。
- 迁移计划：beta.28 表 → Core/App 表，字段映射、回退。
- hello-world App 和最小 App Host 原型。

验收：

```text
install → start → call Core API → stop → update → remove
```

在干净的 macOS、Windows 上通过，且不要求用户手动装 Python。Linux 后续再做。

退出/杀停：

- 任一 P0 契约问题未解决 → 停止，不进入 M1。
- hello-world 在两个平台无法完成生命周期 → 停止。

## M1 · Core v0

**目标：** 最小可用 Core，真实 App 可以依赖。

交付物：

- Core 包与 CLI：`start`、`stop`、`status`、`doctor`。
- `/v1/items`、`/v1/blobs`、`/v1/tags`、`/v1/search`。
- App Host：安装/启动/停止/更新/移除。
- 备份/恢复。
- 签名包校验。
- 本机 capability token。
- 最小 Web 壳：诊断 + App 启动。

验收：

- Core 契约 §12：10/10。
- 补充 Core 测试至少 8/10（启动时间、内存、1 万条搜索、并发写、损坏库、token 权限、App 超时、App 崩溃、备份格式、截断恢复）。
- 一个非 Report 示例 App 完成完整生命周期。
- 示例 App 稳定运行 24 小时。

退出/杀停：

- App Host 无法让示例 App 稳定 24 小时 → 不进入 M2。

## M2 · Report v0 + 安装器

**目标：** 第一个真实产品与主要分发入口。

交付物：

- Report App：reports、sources、evidence、阅读 UI、每日内容。
- Report 安装器：检测 Core；缺则用 uv 安装；安装 Report；启动；打开本地 UI。
- `daily` 内容包 apply/rollback。
- beta.28 数据迁移工具（若 M0 批准）。

验收：

- App 契约 §11：8/8。
- 分发测试至少 10/13。
- 5 名技术用户在干净机器 10 分钟内安装成功。
- 不注册也能使用全部本地 Report 功能。
- 卸载 Report 保留 Core 和用户数据。

退出/杀停：

- 干净 macOS/Windows 安装失败 → 不进入 M3。
- 安装器创建重复工作区 → 停止修复。

## M3 · Project v0 + 更新通道

**目标：** 第二个 App 与稳定更新模型。

交付物：

- Project App：projects、tasks、decisions、evidence、agent roles、handoffs、reviews。
- Core 软件更新。
- App 软件更新。
- 内容更新。
- App 层权益更新。

验收：

- 四条更新通道独立运作。
- Core 更新失败回滚。
- App 更新失败回滚。
- 内容更新失败回滚。
- 离线模式全部优雅降级。

退出/杀停：

- 任一更新通道导致数据丢失或 Core 无法启动 → 不进入 M4。

## M4 · 技术 Beta

**目标：** 用目标小众用户验证真实使用。

交付物：

- macOS / Windows 安装器。
- 安装、用户、App 开发者文档。
- 发布清单与校验/签名。
- 迁移与卸载说明。

验收：

- 分发模型 §7：8/8。
- 三份契约全部验收测试通过。
- 20 名技术用户完成安装并完成第一次有意义任务。
- 收集 30 天留存与付费意愿。
- 至少 3 名用户愿意为 Report/Project 付费。

退出/杀停：

- 安装或留存失败 → 停止、并入 TAA，或退回 CLI-only 项目资产工具。
- 本阶段前不新增 App。

## 关键路径

```text
Process contract
→ Core items/API
→ App Host
→ Report installer
→ Report app
→ Project app
→ update/content channels
→ technical beta
```

## 明确不做

- 用户账号、登录、多用户、团队
- 聊天、房间、社交 feed
- 任务派发、Agent 执行
- 联邦、对等同步、隧道
- 插件市场
- Core 内计费
- 把原生二进制作为 M0 要求
- 大众市场 onboarding

## 下一步

写 Process Contract 与 Python/uv Runtime Contract，然后用 hello-world App 在 macOS、Windows 验证。Linux 后续再做。

M0 通过前不写产品代码。
