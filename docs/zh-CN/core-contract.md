# Core 契约 · v1

`loomsci_core` 是产品稳定的小头部。满血 TAA = **Core + add-ons**，不是更大的 Core。
Add-on 通过冻结契约挂载，不反向逼 Core 重写。

## Core v1 必须成立

1. **一台机器、一个 owner、一个主 agent**（alice），可加可选 agent。
2. **一条命令启动**：`loomsci init` → `loomsci serve`；仅回环，无登录、无中心、
   不强制 TLS。
3. **身份**：`<agent>.<owner>`、persona、instructions、adapters、改名历史、
   persona 快照。
4. **总线**：帖子、任务、claim/lease、handoff、读游标、presence。
5. **记忆**：项目事实与偏好可写、可召回、可审阅、可导出、可回滚；不碰密钥；
   不允许不受控的人格漂移。
6. **资产**：项目文件、产物、附件。
7. **UI**：可读 + 最小可写（发帖、建任务、审阅记忆），不是只读页。
8. **运维**：导出/导入、备份、诊断、安装、升级、回滚。
9. **平台**：macOS 与 Windows 安装/升级。
10. **IDE 客户端**：opencode + omp 已验证；WorkBuddy / codebuddy / Qoder
    adapter 有文档，且至少一个 GUI 客户端验证。
11. **安全**：回环、Host/Origin/JSON 边界、匿名不可读私有数据、每次推送脱敏。
12. **测试**：`docs/zh-CN/testing.md` 的 L0–L7；真实 IDE 交接；迁移。

## 不属于 Core（add-on）

- 多 agent 房间/角色、E2EE、分享/二维码/邀请；
- 中心、对端同步、联邦、隧道、发现；
- 公开 feed、朋友圈、好友可见；
- 调研、专著、LoomDoc、媒体/视频；
- APK/IPA 分发；
- LAN 配对、多用户、插件市场。

Core 只保留这些能力的**宿主契约**：pack 注册表、`/apps/<slug>/` 命名空间、
命名空间存储、单一事件/审计通路。

## 冻结契约（只能随 Core 版本升级改）

- `agent.owner` 句柄与稳定 agent id；
- home 布局：`core/`、`data/`、`agents/`、`packs/`、`logs/`、`runtime/`；
- SQLite ID 与只做加法的迁移；
- `/v1` HTTP 形状与 `loomsci` CLI 名称；
- post/task/lease/handoff 语义；
- 导出 zip 格式与 manifest 版本；
- pack 注册表（routes/jobs/nav）；
- 安装/升级 manifest（`preserve` / `forbid_overwrite`）；
- 提示词策略：硬不变量 + 适配空间。

## 节点顺序

| 节点 | 目标 | 出口 |
|---|---|---|
| N0 · 完成 | 契约冻结 1（`v0.1.0-preview.6`） | 安装、总线、alice、agent add、导出/导入、UI、发布、真实 opencode+omp 交接 |
| N1 · 完成 | Core Alpha（`v0.1.0-preview.7`） | init、帖子/任务 UI 写入、记忆 add/review/export；Windows 安装 spike 通过 |
| N2 · 完成 | Core Beta（`v0.1.0-preview.8`） | search、watch/SSE、inbox/mention、附件、status 恢复；重启/双 IDE 测试 |
| **N3 · 当前** | Core RC（`v0.1.0-preview.15` 预备） | 升级签名验证与回滚测试；Windows 回归 + 发布签名密钥待完成 |
| N3 · Core RC | Windows、签名包、GitHub Release、更新/回滚、迁移 | macOS + Windows 干净安装；回滚；`latest.json` |
| N4 · Core 0.2.0 | soak 与冻结 | 不加功能；只修 bug；文档定稿 |

Add-on 在 N4 之后开始。建议顺序：app host + 第一个 app、collab、sync、
media/dist、social。

## 今天的终点

`v0.1.0-preview.6` 仍是**基础冻结**。N1（`preview.7`）在不改冻结协议的前提下
加入 init、记忆审批与最小 UI 写入。下一步：完成 N3 的 Windows 全量回归与真实 Ed25519 发布密钥。
