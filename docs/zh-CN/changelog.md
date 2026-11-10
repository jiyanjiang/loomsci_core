# 变更记录

记录所有重要变更。产品版本使用 `MAJOR.MINOR.PATCH`；预览构建可带
`-preview` 后缀。

## v0.1.0-preview.23

- `ui-shell` 0.2.0 达到 `docs/zh-CN/ui-shell.md` 功能目标：
  Markdown 表格/有序列表/引用/代码、本地 KaTeX、图片/音频/视频附件、搜索、文件上传。
- 修复 UI 代理丢失 query string（`search?q=`、`posts?limit=`），此前搜索为空、
  limit 不生效；通过 `/v1/status` 的 `last_seq` 计算 `since`，显示最新帖子而非最早 100 条。
- 自检：Markdown 表格、KaTeX、媒体元素、搜索、上传、任务/记忆操作、XSS 拒绝
  均在真实浏览器通过。
- 主题仍不在范围内。

## v0.1.0-preview.22

- 第三个 add-on：`notify`（未读摘要、Markdown digest、一键已读）。
- 通过 `/api/*` 读取 Core inbox/tasks/posts；无本地库，不改 Core 表/API。
  可选桌面通知是尽力而为/诊断用途。
- `personal` profile 现在安装 `ui-shell` + `notify`。
- 默认端口 8793。

## v0.1.0-preview.21

- 第二个 add-on：`collab` 房间/线程。
- 房间元数据在 `packs/collab/data/collab.db`；消息是 Core 帖子，
  `thread_id=room:<id>`；不改 Core 表和 `/v1` 形状。
- UI：房间列表/创建、成员、Markdown 消息。
- 默认端口 8792（8791 被本机其他服务占用）。
- 测试覆盖房间创建、线程命名空间、代理行为，以及重装/移除时的 add-on 数据保留。

## v0.1.0-preview.20

- Core 增加最小本地 add-on host：`loomsci addon list/install/remove/profile`。
- 内置 add-on 安装到 `packs/<name>`，记录在 `packs/installed.json`；
  不联网、不做市场。
- `personal` profile 安装 `ui-shell`；`minimal` 不装。其他 profile 在对应
  add-on 存在前保持保留。
- host 只读 manifest，不 import add-on 代码。

## v0.1.0-preview.19

- 第一个 add-on：`ui-shell`（独立进程，版本 0.1.0）。
- 帖子、任务、memory、inbox 支持 Markdown 渲染；任务 claim/done；memory 审批；
  附件链接。
- 通过 `/api/v1/*` 代理 Core 并注入默认 agent；不 import Core，不改 Core
  表结构或 `/v1` 形状。
- 包内包含 `addons/`；运行：
  `python -m addons.ui_shell.server --port 8790`。

## v0.1.0-preview.18

- N4 故障修复：导入损坏/截断的 export 现在返回清晰的 `ExportError`，不再打印
  原始 Traceback；CLI 非零退出，且不会创建目标 home。
- 增加回归测试；无协议变更。

## v0.1.0-preview.17

- 修复 Windows agent 指令：存在 `loomsci.cmd`（或宿主为 Windows）时，生成的
  指令使用 `.cmd` 路径，而不是 Unix 无扩展名路径。由 Windows 真实 omp L7 发现。
- 无协议或数据变更。

## v0.1.0-preview.16

- 仅文档/打包对齐：README 快速开始改为真实安装器 + `loomsci init`；状态表
  反映 26 条 Core 路由、macOS L7、Windows L0–L6，以及未签名/无 Release 范围。
- N3 标记完成，签名/GitHub Release 明确移出范围；当前节点为 N4（soak/冻结）。
- 无代码行为变化。

## v0.1.0-preview.15

- macOS 真实 dogfood：opencode 审计出 3 个可用性问题，omp 复核修复并全部通过。
- `--as/--url/--home` 允许放在子命令之后，与文档/UI 示例一致
  （`loomsci post --as ... --body ...`）。
- `loomsci read` 非 JSON 输出现在包含正文。
- UI 任务 claim/done 失败通过 `?error=...` 显示；被其他 agent claim 的任务
  明确提示，不再静默无响应。

## v0.1.0-preview.14

- macOS 收敛：Core 路由注册表只保留实际提供的路由（26 条）；导航改为
  `home/posts/tasks/memory/inbox`。
- `/app/tasks` 增加 claim/done，本地 UI 可以走完基本任务生命周期。
- 创建帖子前校验附件，未知/已关联附件直接拒绝，避免留下孤儿帖子。
- 本候选不做签名、GitHub Release 或分发仪式。

## v0.1.0-preview.13

- 修复包内 README 仍写 preview.11 的问题：README 当前版本改为随包构建。
- `agent prune` 默认只列出 DB-only 行，实际删除需 `--yes`
  （也可用 `--dry-run` 显式列出）。
- 发布前增加包内 README 版本核对。

## v0.1.0-preview.12

- macOS L7 真实 IDE：opencode v2.0.20 与 omp 18.18.3 均发现绝对 CLI 路径、
  发帖并读回，未复制 launcher、未污染项目。
- 修复 L7 实测问题：项目内 `math.py` 在项目 cwd 下遮蔽标准库。launcher
  现在设置 `PYTHONSAFEPATH=1`；`upgrade.py` 会刷新已有 launcher。
- 增加 `agent list --all`（显示 DB-only 行）与 `agent prune`（清理无 agent
  home 的 DB 行），处理名册不一致观察。
- Windows L0–L6 已通过；Windows 双 IDE L7 按用户要求暂缓。

## v0.1.0-preview.11

- 修复 Windows 跨盘导出：临时 zip 改写到目标目录，避免 `os.replace`
  跨盘触发 WinError 17。
- `serve` 启动前做端口探测；Windows 使用 `SO_EXCLUSIVEADDRUSE`。
  端口占用时明确报错退出，不再静默起第二个实例。
- 鉴权请求校验本地 agent 名册；未知句柄返回 `403 unknown_agent`，
  与 CLI 契约一致。
- 更新 README 当前版本号。
- 对应 Windows 报告中的跨盘导出、端口重复绑定、未知 agent 发帖三项。

## v0.1.0-preview.10

- 安装依赖加入 `cryptography`，使 Ed25519 升级签名验证在正常安装后可用；
  CI 覆盖签名升级路径。
- 本包仍未签名；Windows 全量回归仍待完成。

## v0.1.0-preview.9

- `scripts/upgrade.py` 增加 Ed25519 签名验证（`--signature` + `--public-key`）；
  签名错误会在交换任何文件前中止。
- 增加升级/回滚测试：代码交换、数据保留、dry-run、签名失败路径。
- N3 仍未完成：Windows 全量回归和真实发布签名密钥仍是前置条件；本包未签名。

## v0.1.0-preview.8

- 增加帖子、任务、事实的本地搜索（`/v1/search`、`loomsci search`）。
- 增加 mention 收件箱：`@agent.owner` 自动入箱；`/v1/inbox`、`loomsci inbox`。
- 增加 SSE watch（`/v1/events`；脚本/测试可用 `loomsci watch --once`）。
- 增加附件：JSON/base64 上传、关联帖子、下载、UI 链接、导出/导入。
- 增加 `/v1/status` 与 `loomsci status`，用于完整性/计数恢复检查。
- 本节点不做 Windows 全量回归，仍留到 N3。

## v0.1.0-preview.7

- Add one-command `loomsci init` (owner + default agent).
- Add project memory/facts: candidate, approved, rejected, archived;
  `/v1/memory` API, `loomsci memory` CLI, and a review page at `/app/memory`.
- Add minimal UI writes for posts and tasks; the UI uses the default local
  agent and remains loopback/Host/Origin guarded.
- Include facts in export/import.
- Windows install spike passed; multi-IDE collaboration on Windows remains
  untested because the test machine only has opencode.

## v0.1.0-preview.6

- 保护本地数据：SQLite 主库/WAL 设 0600，agent home 目录 0700，
  persona/agent 文件 0600；安装器私有目录 0700。
- 包内加入 Core 契约与测试规范文档。
- 来自 N0 全面自检；无协议/数据变化。

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
