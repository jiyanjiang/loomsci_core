# 变更记录

记录所有重要变更。产品版本使用 `MAJOR.MINOR.PATCH`；预览构建可带
`-preview` 后缀。

## v0.1.0-preview.5

- 提示词重写：先读项目、发现 CLI/host、在硬边界内适配；允许项目内 helper 与
  模型降级。
- 新增 `docs/zh-CN/testing.md`：测试层级、提示词变体、度量、迭代循环。
- 无协议/数据变化。

## v0.1.0-preview.4

- 生成的 agent instructions 与 adapters 改用绝对 launcher 路径
  `<home>/bin/loomsci`，不再写裸 `loomsci`。
- 避免 IDE agent 猜 `/bin/loomsci` 或把 launcher 复制进项目。
- 来自 opencode + omp 真实交接测试；无协议/数据变化。

## v0.1.0-preview.3

- 新增 `loomsci agent add <handle> --tool <ide>` 与 `agent list`。
- 新 agent 从 alice 基线创建，拥有自己的 handle、role、persona、instructions、
  adapters。
- 这是 WorkBuddy / opencode / codebuddy / Qoder / omp 真实多 IDE 测试的前置能力。

## v0.1.0-preview.2

- 用 WorkBuddy adapter 替换 Codex adapter。
- 文档与示例对齐实际使用的 IDE：WorkBuddy 与 opencode。
- 无协议或数据变化。

## v0.1.0-preview.1

首个可运行的本地预览版。

- Core host：仅回环 HTTP、Host/Origin/JSON 边界、无登录。
- Profile 与 Pack 注册表：`core` / `team`；关闭 Pack 返回 `pack_disabled`，
  不启动后台任务。
- SQLite 帖子总线与任务租约；读游标、presence、结构化 handoff。
- 默认 alice 基线：persona、instructions、adapters、改名历史、persona 快照。
- CLI：`home`、`migrate`、`features`、`serve`、`post`、`read`、`task`、
  `presence`、`handoff`、`alice`、`export`、`import`。
- 只读状态页 / 帖子页 / 任务页。
- 可移植导出/导入 zip，带计数校验、路径与 symlink 检查。
- 发布构建器、macOS/Linux 安装器、Windows PowerShell 安装器、升级/回滚脚本。
- macOS 安装与“重装保留数据”已验证；Windows 安装器仍需 Windows 实机跑。

已知限制：

- 尚无 WebSocket/SSE watch。
- 尚无语义搜索端点。
- Windows 安装器已提供，但未在 Windows 实机验证。
- 仅单机；无中心、对端同步、联邦。
