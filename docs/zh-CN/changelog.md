# v0.1.0-beta.22 — UI 修复

- Fix the advanced-provider key label.
- Bump ui-shell to 0.5.1.

# v0.1.0-beta.21 — IDE 矩阵与 add-on 契约

- Add IDE compatibility matrix.
- Document the add-on manifest contract.
- Add `loomsci addon contract`.

# v0.1.0-beta.20 — 高级服务商

- Add Aliyun DashScope and Volcengine Ark advanced settings.
- Expose base URL, model, key, and connection test.
- Keys remain write-only and are never returned.

# v0.1.0-beta.19 — FTS5 搜索

- Add SQLite FTS5 indexes and triggers for posts, tasks, facts.
- Search uses FTS5 with a LIKE fallback.
- Add 10k/50k benchmark script and tests.

# v0.1.0-beta.18 — 项目模板

- Add book, research, and OPC 180-day project templates.
- `project template list/create`.
- Create only into empty/missing targets; never copy existing project data.

# v0.1.0-beta.17 — 项目评估量表

- Add structured project evaluations.
- Add `project evaluate` CLI and evaluations API/UI.
- Human review states: draft, reviewed, approved. No automatic approval.

# v0.1.0-beta.16 — 项目应用注册

- Add project app add/list/check.
- Track registered/running/unreachable status.
- Health checks are read-only; project commands are never executed.
- UI displays app status and a check action.

# v0.1.0-beta.15 — API/Schema 契约

- Add `schema_version` and `schema_migrations` ledger.
- `/v1/health` and `/v1/version` expose `api_version=core/1` and `schema_version`.
- Add-on manifests must declare `api=core/1`.

# v0.1.0-beta.14 — 安全审计

- Add security regression tests for Host, Origin, JSON, and agent boundaries.
- Require HTTPS for non-loopback update/package URLs.
- Re-verify downloaded bytes/SHA before installation.
- Document local-process trust and the absence of a capability token.

# v0.1.0-beta.13 — 更新检查

- Add update status/check/download/apply APIs and CLI.
- Add Settings → Updates UI.
- Verify bytes and SHA-256; install uses pre-upgrade backup and rollback.
- Automatic installation remains disabled; user confirms.

# v0.1.0-beta.12 — 项目评审门禁

- New projects default to `candidate`; only `selected` are active.
- Add completeness, maturity, commercial potential, direction, notes, reviewer.
- Add `project review` CLI and review badges in the dashboard.
- Review is metadata-only; no content is copied.

# v0.1.0-beta.11 — 项目仪表盘

- Add project list/detail/stats/entries APIs.
- Add `/app/projects` and project detail views.
- Show sources, file types, monthly activity, database schemas, apps, recent files.
- Reference-only; no source files are copied.

# v0.1.0-beta.10 — 数据库结构检查

- Add read-only SQLite and DuckDB inspection via `project inspect`.
- Store table/column metadata, row counts, and schema hashes in `project_schemas`.
- No database files are copied or modified.

# v0.1.0-beta.9 — 引用式项目

- Add reference-only project registry and metadata index.
- Add `project register/list/show/refresh/remove`.
- Source files, DuckDB/SQLite databases, and app code are never copied.
- Add `.duckdb` detection.

# v0.1.0-beta.8 — 项目扫描

- Add read-only `loomsci project scan`.
- Detect project roots, metadata, file counts, DB files, and app hints.
- No project content is copied and no project code is executed.

# v0.1.0-beta.7 — 登录启动

- Add `loomsci service install/uninstall/status`.
- macOS 使用 LaunchAgent；Windows 使用当前用户 Startup 文件夹。
- The login item runs `loomsci up --detach`; no silent resident service.
- Core keeps using the same detached runtime state.

# v0.1.0-beta.6 — DeepSeek 服务商设置

- Add a one-field DeepSeek API key form at `/app/settings`.
- Add `/v1/settings/llm/deepseek` and test-connection endpoints.
- Key storage is `config.yaml` 0600; keys are never returned by the API,
  written to logs, or included in backups/exports.
- Summaries and research read the same provider configuration.
- Legacy `llm.deepseek_api_key` remains readable and migrates on save.

# v0.1.0-beta.5 — 运行时控制

- 新增 `up --detach`、`status`、`down`、`open`。
- `up --detach` 关闭终端后 Core 仍运行；runtime 状态写入 `home/runtime/`。
- `status` 报告 PID、端口、health、版本和主 URL。
- `open` 优先 ui-shell，未运行时回退 Core `/app`。
- `status --as <agent.owner>` 保留原有 API 状态行为。

# v0.1.0-beta.4 — UI 路由修复

- ui-shell 现在为 `/app` 及五个视图路径返回界面，不再 404。
- 初始视图从路径解析；导航写入 history，前进/后退恢复视图（BUG-0003）。

# v0.1.0-beta.3 — 列表修复

- 有序列表项之间的空行不再关闭列表并重新从 1 编号；空行按 loose list 处理。
- 同步修复 ui-shell、collab、notify（BUG-0002）。

# v0.1.0-beta.2 — 帖子摘要

- 帖子改为单一 Markdown 正文；移除 `title` 字段，旧数据库迁移时丢弃旧值。
- 800 字符以内直接展示全文；超过 800 字符生成 300–500 字摘要，列表展示摘要
  并提供全文入口。
- 配置 DeepSeek key 时异步生成摘要；无 key 或模型失败时使用本地提取式 fallback。
- 新增 `/v1/posts?view=feed`（长文不返回正文）和 `/v1/posts/<id>` 详情接口。
- 修复 collab / notify 的 ordered list 渲染（BUG-0001）。

# v0.1.0-beta.1 — 公测

第一个公测版。本地、单 owner。范围：

- Core、ui-shell、media、research、notify；collab 可选。
- WorkBuddy 5.9.3 macOS smoke；opencode/omp 已有 L7 记录。
- 通过 `release-manifest.json` 安装并校验 SHA-256。
- 备份、校验、恢复、离线迁移、升级前自动备份。
- 不含实时 sync、social、多用户或代码签名。

# 变更记录

记录所有重要变更。产品版本使用 `MAJOR.MINOR.PATCH`；预览构建可带
`-preview` 后缀。

## v0.1.0-preview.49

- `scripts/upgrade.py` 在替换代码前于 `<home>/backups/` 创建资产 bundle；
  备份失败则中止升级。
- 测试/诊断可用 `--no-backup`。

## v0.1.0-preview.48

- `loomsci setup` 在终端中交互：owner、agent、profile、检测到的 IDE、可选隐藏
  输入的 DeepSeek key；保留非交互 flags。
- API key 只写入权限 0600 的 `config.yaml`，不进入工作区或日志。

## v0.1.0-preview.47

- `loomsci setup` 初始化 owner、agent adapter、profile，并提示下一步 `up`。
- `doctor` 检测 WorkBuddy/opencode/omp/Qoder/Cursor/CodeBuddy，未发现时警告。
- 记录 WorkBuddy 5.9.3 smoke：shell/tool、presence、post、claim、done 通过。

## v0.1.0-preview.46

- 修复 Windows 干净安装：`py`/`python` 不在 PATH 时可用 `-PythonExe`，
  或自动搜索 `python`/`python3.12`；找不到时给出明确错误。
- macOS/Windows 沙箱干净安装验证：安装 → init → profile → doctor → up → health。

## v0.1.0-preview.45

- G4.1 第一步：`loomsci doctor` 检查 home、数据库完整性、Core 可达性、
  add-on 状态、可选工具、DeepSeek 配置和磁盘。
- `loomsci up` 先启动已安装 add-on，再启动 Core。
- 安装器输出提示 `doctor` 和 `up`。

## v0.1.0-preview.44

- 修正资产边界：凡提交到 Core 的附件默认都属于工作区资产，不再按来源或
  扩展名排除。
- Core 之外的下载文件不在扫描范围；若用户下载后提交到 Core，则默认迁移，
  除非显式标记 `backup=reference` / `reference_only=true`。
- `asset classify --backup include|reference` 将排除权交还给用户。

## v0.1.0-preview.43

- P3 v0.1 目标契约：`sync inspect`、`sync import`。
- 可导入“已安装但无用户数据”的工作区；拒绝 used/unknown 目标。
- 保留本地 config、add-on 代码；源 bundle 不存在的默认 agent 移到
  `runtime/pre-import-agents/`。
- 恢复时执行 additive schema migration，旧 bundle 仍可导入。
- 仅离线：AirDrop/U 盘/邮件传输；无网络 daemon。

## v0.1.0-preview.42

- 附件来源元数据 `meta_json`：`origin`、`asset_kind`、`rights`、
  `source_url`、generator。
- `asset list --unclassified`、`asset classify` 用于存量附件分类。
- 文档边界改为按来源：AI/人生成的 PDF/PPT/EPUB 包含；下载资料只保留元数据；
  未知文档默认迁移包含，可用 `--unknown-documents` 调整。
- 生成/下载的音频、视频同样按来源处理。

## v0.1.0-preview.41

- `backup verify` 校验 bundle hash、SQLite 完整性、附件和 Markdown 投影。
- `backup prune --dir --keep` 实现保留策略；默认 dry-run，只处理有效资产 bundle。
- `storage report` 区分 hardlink 去重前后的逻辑 blob 与实际磁盘占用。

## v0.1.0-preview.40

- P2.6 第一步：`storage report`、`storage duplicates`、`storage dedupe`、
  `storage prune`、`storage compact`（破坏性操作默认 dry-run）。
- dedupe 用 hardlink 合并重复附件 blob；报告逻辑与实际磁盘字节。
- prune 只删除超过 `--older-than`（默认 3600s）的孤儿 blob。
- compact 仅在 `--apply` 时执行 WAL checkpoint 和 `VACUUM`。

## v0.1.0-preview.39

- P2.5 资产 bundle：`backup create`、`backup show`、`backup restore`。
- bundle 包含一致性 SQLite 快照、Markdown 投影、内容寻址资产、
  `attachments.json`、`references.json`、`excluded.json`。
- 重复附件共享一个资产对象；恢复时优先 hardlink。
- 默认秘密阻断导出；`--redact` 生成脱敏副本且不改源；`--allow-secrets`
  为显式危险覆盖。
- 第三方 PDF 只进入 `references.json`，不包含二进制。

## v0.1.0-preview.38

- P2.5 第一步：只读 `loomsci backup inspect` / `--json`。
- 分类资产、第三方参考资料、派生/缓存、排除的 runtime/代码和秘密内容。
- 按 SHA-256 检测重复附件对象并估算可回收空间；不修改数据。
- 边界文档：`docs/zh-CN/backup.md`。

## v0.1.0-preview.37

- ui-shell v0.5.0：可编辑站点名称、logo、链接和页脚。
- 缺省值：站点名 `loomsci`，logo
  `https://www.loomsci.com/nav-logo.png`；配置存
  `packs/ui_shell/data/site.json`。
- `GET /api/site` 返回生效配置；`POST /api/site` 持久化。不改 Core 表/API。
- 页头和页脚使用保存后的品牌信息；壳层内提供设置页。

## v0.1.0-preview.36

- ui-shell v0.4.0：英文 / 简体中文界面，自动检测语言并提供语言选择；选择
  存入浏览器 localStorage。
- 壳层文案集中到 `addons/ui_shell/web/i18n.js`；用户内容不翻译。
- add-on server 绑定端口不再做反向 DNS（macOS CI 修复）。

## v0.1.0-preview.35

- add-on 生命周期 v1：manifest 增加 `package`、`entry`、`port`、`health`；
  安装代码位于 `packs/<package>/`。
- `packs/installed.json` 记录版本、包名、目录哈希和安装时间。
- `addon update [name|--all]` 替换代码并保留 add-on 数据。
- 新增 `addon verify`、`addon start/stop/status`；运行时使用 home venv，
  拒绝占用端口，检查健康，并把日志/状态写到 home。
- `requires` 支持 add-on 依赖（`core/1` 以及可选 `name>=version`），
  在安装/更新时校验。
- `team` / `full` profile 与当前自带目录一致；文档改用真实命令
  `addon profile`。
- media worker 按安装包解析（`packs.media.worker`），OCR/转写从 `packs/`
  运行也可用，不再只依赖源码目录。
- add-on 提供本地 `/api/health`，运行状态不依赖 Core 是否在线；Windows
  add-on 从 SSH job 脱离，并按实际监听 PID 跟踪。
- add-on server 绑定端口时不再调用 `socket.getfqdn()`，消除 macOS CI
  反向 DNS 卡顿；launcher 显式插入 home 路径。

## v0.1.0-preview.34

- media v0.2b：可选 RapidOCR 与 faster-whisper。
- `POST /api/ocr/<attachment>`、`POST /api/transcribe/<attachment>`；GET
  返回缓存结果。工具缺失返回 `*_not_available`。
- OCR：RapidOCR 1.4.4 + onnxruntime；转写：faster-whisper 1.2.1，
  `small` int8；固定 `av==17.1.0` 以兼容。
- 跨平台稳定固定：onnxruntime 1.20.1、ctranslate2 4.4.0、av 17.1.0、
  setuptools 80.10.2；提取在独立 worker 进程运行。
- macOS + Windows 实测：OCR 识别 "HELLO OCR 123"；4.5s 中文音频转写
  文本完全正确；两端缓存均生效。
- 可选依赖在 `addons/media/requirements-media.txt`，不进 Core。

## v0.1.0-preview.33

- research v0.2：可选 DeepSeek Search + Chat，带来源约束回答。
- Key 解析：`DEEPSEEK_API_KEY`/`DS_KEY` > `<home>/config.yaml`
  `llm.deepseek_api_key` > 旧 `~/.taa/config.toml`；key 不写日志。
- `/retrieve` 写入真实搜索来源；`/ask` 写草稿并走同一确定性 gate，
  只有通过才可发布。
- UI 增加 Retrieve sources / Ask DeepSeek；浏览器不接触 key。
- 真实测试：Python 3.12 发布日，6 条搜索来源 + 官方来源，gate 通过；
  macOS 与 Windows（环境变量 key）。

## v0.1.0-preview.32

- media v0.2a：通过 ffmpeg 生成图片/视频缩略图，缓存到
  `packs/media/data/thumbs`；UI 使用缩略图/poster，失败回退原图。
- 增加 `/api/capabilities` 检测 ffmpeg/tesseract/whisper。OCR 与语音转写
  尚未实现，属于 v0.2b；工具缺失时不得假装成功。
- 不改 Core 表/API。

## v0.1.0-preview.31

- 第五个 add-on：`research` v0.1（确定性，不调 LLM）。
- 工作区 `r-<hash>/vN`；来源 URL/标题/摘录/分级；事实必须引用已有来源；
  `fact_gate` 要求 2 个域名、1 个强来源、2 条引用、切题性、abstain 处理。
- 只有 gate 通过的稿才可发布到 Core；不改 Core 表/API。
- 默认端口 8796；`maker` profile = ui-shell + media + research。
- 复用 TAA 的 SOP 与 fact gate 纪律，不复用其存储/config/rooms/jobs。

## v0.1.0-preview.30

- 修复截图粘贴失败的真正原因：Flask 1MB 请求体上限导致 `body_too_large`
  HTTP 413，且存储附件上限只有 512KB；真实截图通常超过两者。
- 请求上限提升到 24MB，附件上限提升到 16MB；本地边界不变。
- 真实 2.8MB PNG 经系统剪贴板粘贴后可上传并在帖子中渲染（1200x800）；
  增加 >512KB 附件回归测试。
- 无协议/数据形状变更。

## v0.1.0-preview.29

- 修复 POSIX 下端口处于 `TIME_WAIT` 时 `serve` 预检误报：POSIX 探测使用
  `SO_REUSEADDR`，Windows 继续 `SO_EXCLUSIVEADDRUSE`。
- 无协议/数据变更。

## v0.1.0-preview.28

- `ui-shell` 0.3.4 粘贴诊断与兜底：
  - 静态资源 `no-store` + 版本号，避免旧 JS 缓存；
  - paste 监听放到 document，焦点不必在 textarea；
  - 增加“Paste image from clipboard”按钮，走 `navigator.clipboard.read`；
  - 同时支持 `clipboardData.files`/`items` 与拖放。
- 真实 macOS 剪贴板 + 有头 Chromium 已复现粘贴 chip；之前的合成事件测试不算充分证据。
- 不改 Core 表/API。

## v0.1.0-preview.27

- `ui-shell` 0.3.2 剪贴板加固：同时支持 `clipboardData.files` 与
  `clipboardData.items`，补齐无名粘贴文件，剪贴板没有图片文件时给出提示，
  并支持图片拖放。
- 粘贴仍是 `ui-shell` 输入层能力，不属于 `media`。
- 不改 Core 表/API。

## v0.1.0-preview.26

- `ui-shell` 0.3.1：可直接从剪贴板粘贴图片到正文编辑器；提交时上传并附加。
- 这是 `ui-shell` 输入层能力，不属于 `media`；`media` 仍只做媒体库/预览。
- 不改 Core 表/API。

## v0.1.0-preview.25

- 第四个 add-on：`media` v0.1（基于 Core 附件的媒体库）。
- 索引帖子，按 image/audio/video/file 分类，通过 `/api/attachment/<id>`
  预览/播放；无本地库，不改 Core 表/API。
- 转码、缩略图、OCR/转写明确留到 media v0.2。
- 默认端口 8794。

## v0.1.0-preview.24

- `ui-shell` 0.3.0 baseline theme：单一 token 源、跟随系统明暗、WCAG-AA
  对比度、可见键盘焦点、36px 控件、360px 响应式。
- 不做主题切换、品牌、i18n、开版；这些保持独立/后续。
- 自检：正文对比度 15.7:1/16.6:1，muted 5.9:1/8.3:1，2px 焦点，
  360px 无横向滚动。

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
