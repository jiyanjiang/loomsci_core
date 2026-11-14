# LoomSci Core + Apps 契约评审结论

## 0. 总体判定

**有条件通过。**

三份契约在方向上是自洽的：Core 收缩为本地优先运行时、App 承载领域模型、分发以 Report 为入口、更新通道分离——这个架构判断是对的。但契约目前停留在"意图声明"层面，缺少可执行的协议细节、失败语义、安全边界和分发落地路径。按当前文本直接进入实现，会在第 3–4 周遇到不可逆的返工。**可以继续，但必须先补齐 P0 项，否则 M1 不应启动。**

---

## 1. 阻断问题

### P0-1：App 与 Core 之间的进程边界未定义

契约反复说"App 是独立进程""Core 不导入 App 代码"，但从未定义 App 如何被启动、如何与 Core 通信、如何接收 scoped token、如何被健康检查。

`app-manifest.md` 第 6 节 Lifecycle 说"launch entry with scoped token"，但没有定义：

- App 是子进程还是独立进程？Core 退出后 App 是否存活？
- App 如何获得 token？环境变量？stdin？启动参数？HTTP header？
- App 调用 Core API 时，token 放在哪里？`Authorization: Bearer`？自定义 header？
- App 的 `entry: "server"` 是什么？Python 模块？WSGI app？可执行文件路径？
- Core 如何知道 App 已就绪？轮询 `/health`？超时多少？失败几次算启动失败？
- App 崩溃后 Core 是否自动重启？重启策略是什么？

**没有这些定义，`app/1` 和 `core/1` 都只是纸面版本号。** 这是整个架构的承重墙，必须先于任何数据模型讨论。

**要求：** 在 `app-manifest.md` 中新增一节 "Process contract"，定义启动协议、token 传递、健康检查协议、退出码语义、stdout/stderr 约定、崩溃处理。给出一个最小可运行的伪代码示例。

---

### P0-2：签名体系没有密钥模型

三份契约反复要求"签名验证"，但没有任何一处定义：

- 签名密钥由谁持有？Core 仓库？App 仓库？独立发布密钥？
- 密钥如何轮换？泄露后如何撤销？
- 签名格式是什么？minisign？ed25519 裸签名？JWS？PGP？
- 公钥如何分发？硬编码在 Core 二进制中？首次运行时从何处获取？
- 离线安装时如何验证签名？公钥随安装包分发？
- Content pack 的签名密钥与 App 的签名密钥是同一把还是分开？

`distribution-model.md` 第 3 节列出了 `signature` 字段，但没有定义签名算法、密钥管理、信任链。**没有密钥模型，"签名验证"是不可实现的。**

**要求：** 新增 "Signing and trust" 一节，定义：密钥层级（root / release / content）、算法（建议 ed25519）、公钥分发方式、轮换流程、撤销流程、离线验证路径。

---

### P0-3：`items.cross_read` 权限与"App 隔离"硬保证矛盾

`core-contract.md` 第 2 节硬保证第 4 条说"App isolation. Each app has its own package, data namespace, port, and health path." 第 12 节验收测试第 10 条说"an app cannot read another app's namespace through Core APIs."

但 `app-manifest.md` 第 5 节定义了 `items.cross_read` 权限："read items from other apps (explicit approval)"。

这两个条款直接冲突。如果 `cross_read` 存在，那么"不能读另一个 namespace"就不是硬保证；如果隔离是硬保证，那么 `cross_read` 就不应该出现在 v0 权限集中。

**要求：** 二选一：

- **方案 A（推荐）：** v0 删除 `items.cross_read`。App 间共享通过 Core 的显式导出/导入 API 完成，或者推迟到 v1。验收测试第 10 条保持原样。
- **方案 B：** 保留 `cross_read`，但必须定义"explicit approval"的完整流程：谁批准？用户在哪里确认？批准是 per-app 还是 per-item？批准状态存在哪里？撤销后已读数据如何处理？同时修改验收测试第 10 条。

**建议选 A。** v0 的隔离性比互通性重要得多。互通做错了会毁掉安全模型，做对了也没人在 v0 用。

---

### P0-4：备份/恢复的语义未定义

`core-contract.md` 第 6 节 API 面有 `GET /v1/backup`、`POST /v1/backup`、`POST /v1/restore`，但没有任何一处定义：

- 备份包含什么？Core 数据 + 所有 App 数据？还是可选？
- 备份格式是什么？SQLite dump？文件树 tar？自定义格式？
- 恢复是覆盖还是合并？恢复到空 workspace 还是现有 workspace？
- 恢复时 App 版本不匹配怎么办？
- 备份是否包含 App 代码？还是只备份数据？
- 备份是否包含 local.token？如果包含，恢复后 token 是否失效？
- 部分恢复（只恢复某个 App 的 namespace）是否支持？

验收测试第 3 条说"an item with Markdown and a blob survives restart, backup, restore"，但"survives"的定义太模糊。

**要求：** 新增 "Backup and restore semantics" 一节，定义备份范围、格式、恢复模式（全量覆盖 / 合并 / 选择性）、失败语义、版本兼容规则。至少给出备份文件的结构描述。

---

### P0-5：`0.1.0-beta.28` 的迁移路径是"愿望清单"而非"计划"

`core-contract.md` 第 11 节列了 5 步迁移路径，但没有：

- 每一步的负责人、时间估算、验收标准
- 迁移工具是 Core 的一部分还是独立脚本？
- 迁移是自动的还是用户手动触发？
- 迁移失败后如何回退？
- 迁移期间用户数据是否可访问？
- `posts` → `items` 的映射规则：`posts` 的哪些字段进 `items`，哪些进 `metadata_json`？
- `attachments` → `blobs` 的映射：文件路径如何变成 content-addressed blob？
- `facts` 和 `projects` 表迁移到哪个 App？如果用户只装了 Core 没装 Report，这些数据去哪？

**要求：** 迁移计划必须具体到字段映射和工具行为。如果迁移工具不在 M1 范围内，明确说"beta.28 用户数据在 v0 发布时不被迁移，提供导出脚本作为过渡"，不要假装有迁移路径。

---

### P1-1：`max_core` 的存在理由不充分

`app-manifest.md` 第 3 节把 `max_core` 标为 optional，但第 9 节说"`min_core` / `max_core` gate installation"。如果 Core API 在 `core/1` 内是加法的（`core-contract.md` 第 2 节硬保证第 3 条），那么 `max_core` 在同一个 major 内不应该存在。App 声明 `max_core: "0.9.99"` 意味着它预期 Core 0.10.0 会破坏它——但如果 Core 遵守加法兼容承诺，0.10.0 不应该破坏任何 `core/1` App。

**要求：** 删除 `max_core`，或者明确说明它在什么场景下使用（例如：App 使用了 Core 的 deprecated API，预期在某个版本被移除）。如果保留，必须定义 Core 在 `core/1` 内移除 API 的流程。

---

### P1-2：`requires_registration` 字段的语义模糊

`app-manifest.md` 第 3 节定义了 `requires_registration: bool`，注释说"app-level only; Core never requires it"。但：

- 如果 App 声明 `requires_registration: true`，Core 是否拒绝安装？
- 还是 Core 安装它，但 App 自己处理注册？
- 如果用户不注册，App 的哪些功能可用？
- 这个字段对 Core 的行为有什么实际影响？

**要求：** 明确这个字段是"声明性元数据"还是"Core 强制执行的门控"。如果是声明性的，它不应该在 manifest 的 required fields 中；如果是强制性的，必须定义 Core 的行为。

---

### P1-3：Content pack 的 `items` 结构与 Core `items` 的关系未定义

`app-manifest.md` 第 8 节给出了 content pack 的 JSON 示例，其中 `items` 数组的元素有 `id`、`title`、`url`、`summary`、`tags`。但 Core 的 `items` 表有 `app`、`type`、`body`、`metadata_json` 等字段。Content pack 的 item 如何映射到 Core 的 `items` 表？

- `url` 和 `summary` 进 `metadata_json`？
- `type` 是什么？`content`？
- 如果 content pack 的 item id 与已有 item 冲突怎么办？
- Content pack 回滚时，已写入 Core 的 items 如何回滚？

**要求：** 定义 content pack item → Core item 的映射规则，以及回滚时的数据操作语义。

---

### P1-4：App 数据 namespace 的物理位置与 Core 数据模型的关系未定义

`core-contract.md` 第 4 节 workspace layout 显示 `apps/<slug>/data/` 是 App 的 namespace。但第 5 节 Core 数据模型中 `items` 表有 `app TEXT NOT NULL` 字段。这意味着 App 的数据可能存在于两个地方：

- `apps/report/data/` 下的 App 自有数据库
- `data/core.db` 中 `items` 表的 `app='report'` 行

这两者是什么关系？App 的 domain 数据（reports、sources）存在自己的数据库里，还是存在 Core 的 `items` 表中？如果都存在，什么数据进哪里？

**要求：** 明确数据分层规则：Core `items` 是"通用原语"，App 自有数据库是"领域模型"。给出一个具体例子：Report 的一篇 report 在 Core `items` 中是什么样，在 Report 自有数据库中是什么样，两者如何关联。

---

### P2-1：`events` 表的用途和保留策略未定义

`core-contract.md` 第 5 节定义了 `events` 表，但没有任何 API 读写它，也没有说明它的用途。是审计日志？是 App 间通信？是更新历史？

**要求：** 要么定义 `events` 的用途、API 和保留策略，要么从 v0 数据模型中删除。

---

### P2-2：`GET /v1/backup` 的语义不明确

`GET /v1/backup` 是列出备份历史？还是下载最新备份？还是触发备份？HTTP GET 通常不应有副作用，但"backup"听起来像操作。

**要求：** 明确 `GET /v1/backup` 的语义。如果是列出备份，改为 `GET /v1/backups`。

---

### P2-3：`port` 字段的冲突处理未定义

`app-manifest.md` 第 3 节说 `port: 0` 表示 Core 分配，但固定端口（如 8791）冲突时怎么办？Core 是否检查端口占用？冲突时拒绝启动还是自动分配？

**要求：** 定义端口冲突的处理规则。

---

## 2. 内部一致性

三份契约之间存在以下矛盾或张力：

| # | 位置 | 矛盾 | 严重度 |
|---|---|---|---|
| 1 | `core-contract.md` §2.4 vs `app-manifest.md` §5 | App 隔离硬保证 vs `items.cross_read` 权限 | **P0**（见 P0-3） |
| 2 | `core-contract.md` §2.3 vs `app-manifest.md` §3 | Core API 加法兼容 vs `max_core` 门控 | **P1**（见 P1-1） |
| 3 | `core-contract.md` §5 vs `app-manifest.md` §8 | Core `items` 表结构 vs content pack `items` 结构 | **P1**（见 P1-3） |
| 4 | `core-contract.md` §4 vs §5 | App data namespace 物理位置 vs Core `items.app` 字段 | **P1**（见 P1-4） |
| 5 | `core-contract.md` §1 "Core must remain useful when no app is installed" vs §3 "Minimal web shell may show... generic item reader" | "有用"的定义模糊：generic item reader 是 Core 功能还是准 App？ | P2 |
| 6 | `distribution-model.md` §1 "Shared behavior is tested by contract tests, not by shared source files" vs `core-contract.md` §6 "Exact payloads are frozen in docs/en/app-manifest.md and the SDK examples" | 契约测试需要共享的测试夹具，但"不共享源文件"的边界不清 | P2 |
| 7 | `core-contract.md` §7 "If the token is lost, Core can rotate it; app re-registration is required" vs §12.9 "no registration is required for any local feature" | "re-registration" 与 "no registration" 用词冲突。前者指技术重注册，后者指用户注册，但文本上没有区分 | P2 |

---

## 3. 安全与运维

### 3.1 本地 capability token

当前设计（`~/.loomsci/local.token`，0600 权限，CLI 自动读取，Web shell 同源会话，App 获取 scoped token）方向正确，但缺少：

- **Token 格式：** 随机字节？JWT？长度？熵要求？
- **Token 轮换的触发条件：** 用户手动？检测到泄露？定期？
- **Scoped token 的具体 scope 编码：** 是 JWT claims？是 Core 内部数据库记录？App 的 token 被泄露后如何单独撤销？
- **浏览器场景：** Web shell 是 Core 自己 serve 的页面，同源会话如何建立？Core 的 web shell 是否有登录步骤（输入 token）？还是依赖 localhost 的浏览器安全模型？
- **CSRF：** 如果 token 通过 cookie 传递，localhost 上的恶意网页能否发起跨站请求？

**必须补进契约：** token 格式、scope 编码、轮换流程、浏览器会话建立方式、CSRF 防护策略。

### 3.2 App 隔离

当前设计依赖"每个 App 自己的 namespace + 权限声明"，但缺少：

- **进程级隔离：** App 是否在沙箱中运行？还是与 Core 同用户权限？如果 App 代码有恶意行为（读 `~/.loomsci/core.db` 直接），Core 如何防护？
- **文件系统隔离：** App 代码运行在 `apps/<slug>/code/` 下，但它可以读 `~/.loomsci/` 下的任何文件。Core 如何阻止 App 直接读 `data/core.db` 或其他 App 的 `data/`？
- **网络隔离：** App 是否可以访问外网？如果可以，Core 如何防止 App 将本地数据外传？

**必须补进契约：** 明确 v0 的隔离边界是"逻辑隔离"（通过 API 和权限）而非"安全沙箱"。如果这是有意的，必须在契约中明确声明，避免用户误以为 App 是沙箱化的。如果目标是安全沙箱，需要完全不同的技术方案（容器、seccomp、macOS sandbox-exec 等），这远超当前契约的范围。

### 3.3 签名与回滚

签名体系的问题见 P0-2。回滚方面：

- Core 软件更新失败回滚：回滚到哪个版本？如何保留上一个版本？
- App 更新失败回滚：`app-manifest.md` 第 6 节说"backup current code/data"，但备份存在哪里？保留几个版本？
- Content pack 回滚：回滚是删除新 items 还是恢复旧 items？

**必须补进契约：** 回滚的存储位置、保留策略、触发条件、验证方式。

### 3.4 离线与故障恢复

- Core 启动时如果 `core.db` 损坏怎么办？自动修复？提示用户？
- App 崩溃后 Core 的状态如何？App 的 items 是否仍然可读？
- 更新过程中断电怎么办？是否有事务性更新？

**必须补进契约：** 数据库损坏检测与恢复策略、更新事务性要求。

---

## 4. 分发可行性

### 4.1 Python 运行时：最大的分发风险

`core-contract.md` 第 13 节 Open questions 第一条就是"shipped runtime: bundled Python vs native binary"。这不是一个可以推迟的问题——**它决定了整个分发模型是否可行。**

如果 Core 是 Python 包：

- 用户需要 Python 3.x，这直接违反验收测试第 1 条"a clean machine can install Core without Python knowledge"
- macOS 系统 Python 已被弃用，Windows 默认没有 Python
- 依赖管理（pip、venv、poetry）对普通用户是灾难

如果 Core 是打包的二进制（PyInstaller、Nuitka、Briefcase）：

- 启动时间、包体积、杀毒软件误报
- macOS 签名和公证（notarization）是硬要求，否则 Gatekeeper 会阻止运行
- Windows SmartScreen 对未签名二进制会警告

**最关键风险：macOS 签名和公证。** 没有 Apple Developer 证书和公证流程，macOS 用户无法顺利安装。这不是技术问题，是流程和成本问题（需要 Apple Developer 账号，年费 99 美元）。

**要求：** 在 M0 阶段确定运行时方案。建议：Core 用 PyInstaller 或 Nuitka 打包为单文件二进制，App 作为 Core 管理的 Python 进程运行（App 代码是 Python 源文件，由 Core 的嵌入式 Python 运行时执行）。这样用户只需要安装一个二进制。

### 4.2 安装器

Report 安装器需要处理：

- 检测已有 Core（PATH、workspace metadata、`/v1/health`）
- 下载并验证 Core 包
- 安装 Core 到用户可写位置（`~/.loomsci/core/` 还是 `~/.local/bin/`？）
- 启动 Core
- 安装 Report App
- 打开浏览器

**风险：** 安装器本身是什么？Shell 脚本？Python 脚本？下载的二进制？如果安装器是 Python 脚本，用户还是需要 Python。

**要求：** 安装器必须是单文件可执行文件。macOS 上可以是 `.pkg` 或 `.app`，Windows 上是 `.exe`，Linux 上是 AppImage 或 shell 脚本 + 二进制。

### 4.3 升级

Core 自更新是一个经典难题：

- Core 正在运行时如何替换自己的二进制？
- Windows 上文件锁定问题
- macOS 上签名验证问题

**要求：** 定义 Core 自更新的具体机制。建议：Core 下载新版本到 `runtime/` 目录，验证签名后，下次启动时切换。或者使用外部 updater 进程。

### 4.4 卸载与数据保留

`distribution-model.md` 第 2 节说"uninstall Report leaves Core and user data intact"。但：

- 卸载 Core 时，用户数据是否保留？
- 如果保留，用户如何找到数据？
- 如果删除，是否需要显式确认？

**要求：** 定义 Core 卸载时的数据行为。建议：Core 卸载默认保留 `~/.loomsci/data/`，并提供 `--purge` 选项。

---

## 5. 数据模型

### 5.1 当前模型是否足够？

**对 Report：基本足够。** Report 的 reports、sources、evidence 可以映射到 `items` + `blobs` + `tags`。`metadata_json` 可以承载领域字段。Report 自有数据库可以存储阅读进度、高亮、笔记等。

**对 Project：勉强足够，但有隐患。** Project 的 projects、tasks、decisions、agent roles、handoffs、reviews 需要：

- **关系：** task 属于 project，decision 关联 task，handoff 关联 agent。Core `items` 没有关系字段，只能靠 `metadata_json` 中的外键引用。这在 v0 可以接受，但需要明确约定。
- **结构化查询：** Project 需要按 project 筛选 tasks、按 agent 筛选 handoffs。Core 的 `GET /v1/items` 如果只支持简单过滤，Project 需要把所有 items 拉到本地再过滤。
- **版本历史：** decisions 和 reviews 可能需要版本历史。Core `items` 没有版本字段。

### 5.2 现在必须补的

- **`GET /v1/items` 的过滤和分页语义：** 至少支持 `?app=`、`?type=`、`?tag=`、`?updated_after=`、`?limit=`、`?offset=`。没有这个，App 无法高效使用 Core API。
- **`items` 的 `type` 字段约定：** 是自由字符串还是有命名规范？建议：`app.slug + "." + 领域类型`，如 `report.source`、`project.task`。
- **`metadata_json` 的 schema 约定：** 是完全自由，还是 App 必须声明 schema？建议 v0 完全自由，但要求 App 在 manifest 中声明 `metadata_schema_version`。

### 5.3 可以推迟的

- **关系/图查询：** v0 不需要。App 在自有数据库中维护关系。
- **版本历史：** v0 不需要。App 可以用 `events` 表或自有表实现。
- **全文搜索的高级功能：** 中文分词、语义搜索、ranking 调优。v0 用 FTS5 默认 tokenizer 即可。
- **跨 App 查询：** 如果 P0-3 选择方案 A，v0 不需要。

---

## 6. 验收测试补充

现有验收测试（`core-contract.md` §12、`app-manifest.md` §11、`distribution-model.md` §7）是好的起点，但缺少以下可自动化测试：

### 6.1 Core 层

| # | 测试 | 自动化方式 |
|---|---|---|
| 11 | Core 启动时间 < 3 秒（冷启动，无网络） | CI 计时 |
| 12 | Core 内存占用 < 200 MB（空 workspace） | CI 监控 |
| 13 | 10000 个 items 时搜索延迟 < 500ms | 基准测试 |
| 14 | 并发写入：两个 App 同时写 items 不冲突 | 并发测试 |
| 15 | Core 数据库损坏时启动不崩溃，给出明确错误 | 故障注入 |
| 16 | local.token 权限为 0600，否则 Core 拒绝启动 | 文件权限检查 |
| 17 | App 启动超时（health 30 秒未就绪）时 Core 正确标记失败 | 超时测试 |
| 18 | App 崩溃后 Core 仍然健康，其他 App 不受影响 | 故障注入 |
| 19 | 备份文件可被独立工具读取（不依赖 Core） | 格式验证 |
| 20 | 恢复不完整备份（文件截断）时给出明确错误，不损坏现有数据 | 故障注入 |

### 6.2 App 层

| # | 测试 | 自动化方式 |
|---|---|---|
| 9 | App 声明 `items.write` 但未声明 `blobs.write` 时，尝试上传 blob 被拒绝 | 权限测试 |
| 10 | App 更新后，App 自有数据库 schema 迁移成功，数据完整 | 迁移测试 |
| 11 | App 更新失败后，旧版本仍然可启动 | 回滚测试 |
| 12 | 两个 App 使用相同 `data_namespace` 时，第二个安装被拒绝 | 冲突测试 |
| 13 | App 的 `health` 路径返回非 200 时，Core 正确标记 unhealthy | 健康检查测试 |

### 6.3 分发层

| # | 测试 | 自动化方式 |
|---|---|---|
| 8 | 安装器在无 Python 的 Windows 10 上成功安装 Core | CI（Windows 容器） |
| 9 | 安装器在无 Python 的 macOS 13+ 上成功安装 Core | CI（macOS runner） |
| 10 | 安装器检测到已有 Core 时不重复安装 | 重复安装测试 |
| 11 | 签名验证失败时安装器不留下任何文件 | 清理验证 |
| 12 | 卸载 Report 后 Core 和用户数据完好 | 卸载测试 |
| 13 | 卸载 Core 后用户数据默认保留 | 卸载测试 |

---

## 7. 阶段性节点

### M0：架构冻结（2 周）

**目标：** 解决所有 P0 问题，冻结 `core/1` 和 `app/1` 的协议细节。

**交付物：**

- Process contract（App 启动/通信/健康检查协议）
- Signing and trust 模型
- 数据分层规则（Core items vs App 自有数据）
- 备份/恢复语义
- 迁移计划（beta.28 → v0）的具体方案
- 运行时方案决策（打包方式、安装器形态）

**可量化自检：**

- 所有 P0 项在契约文档中有明确答案
- 一个最小 App（hello-world）可以在 Core 上安装、启动、调用 API、停止、更新、移除
- 签名验证流程有端到端测试

**退出/杀停：** 如果 M0 结束时 P0 项仍有未解决的，**停止项目**。这些是架构基础，不能带着未决问题进入实现。

---

### M1：Core v0 最小实现（4 周）

**目标：** 实现 Core 的最小可用版本，通过 Core 验收测试。

**交付物：**

- Core 二进制（或可安装包）
- `loomsci start` / `stop` / `status` CLI
- `/v1/health`、`/v1/items` CRUD、`/v1/blobs`、`/v1/search`、`/v1/tags`
- App host（install/start/stop/update/remove）
- 备份/恢复
- 签名验证
- local.token 机制

**可量化自检：**

- `core-contract.md` §12 的 10 条验收测试全部通过
- 补充的 Core 层测试（§6.1）至少 8/10 通过
- 一个示例 App（非 Report）可以完整走通生命周期

**退出/杀停：** 如果 App host 无法稳定运行示例 App 超过 24 小时，**不进入 M2**。

---

### M2：Report App v0 + 安装器（4 周）

**目标：** 实现 Report App 的最小可用版本和 Bootstrap 安装器。

**交付物：**

- Report App（reports、sources、evidence 的 CRUD + 阅读 UI）
- Report 安装器（检测/安装 Core、安装 Report、启动）
- Content pack 机制（daily 频道的 apply/rollback）
- beta.28 数据迁移工具（如果 M0 决定做）

**可量化自检：**

- `app-manifest.md` §11 的 8 条验收测试全部通过
- 分发层测试（§6.3）至少 10/13 通过
- 一个从未安装过 LoomSci 的用户可以在 10 分钟内完成安装并创建第一篇 report

**退出/杀停：** 如果安装器在干净 macOS 或 Windows 机器上无法完成安装，**不进入 M3**。

---

### M3：Project App v0 + 更新通道（4 周）

**目标：** 实现 Project App 和完整的更新通道分离。

**交付物：**

- Project App（projects、tasks、decisions、agent roles、handoffs）
- Core 软件自更新
- App 软件更新
- Content 更新
- Entitlement 更新（App 层）

**可量化自检：**

- 四个更新通道独立运作，互不干扰
- Core 更新失败自动回滚
- App 更新失败自动回滚
- Content 更新失败自动回滚
- 离线模式下所有更新通道优雅降级

**退出/杀停：** 如果任何一个更新通道的失败会导致数据丢失或 Core 无法启动，**不进入 M4**。

---

### M4：发布候选（2 周）

**目标：** 完成发布前的全部验证。

**交付物：**

- 签名和公证流程完成（macOS）
- 安装包（macOS、Windows、Linux）
- 文档（安装指南、用户指南、开发者指南）
- 发布清单

**可量化自检：**

- `distribution-model.md` §7 的 8 条发布门全部通过
- 三份契约的全部验收测试通过
- 在 3 台干净机器（macOS、Windows、Linux）上完成安装测试

**退出/杀停：** 如果任何发布门未通过，**不发布**。

---

## 8. 下一步动作

**唯一最优先动作：定义 Process contract（App 与 Core 的进程边界和通信协议）。**

**为什么：**

1. 它是 P0-1，是整个架构的承重墙。没有它，`app/1` 和 `core/1` 只是纸面版本号。
2. 它决定了其他所有决策：数据模型（App 数据如何写入 Core）、安全模型（token 如何传递）、分发模型（App 代码如何打包和运行）、更新模型（App 如何被替换）。
3. 它是最容易被低估的工作。看起来"就是启动一个子进程"，但实际上涉及进程生命周期、错误处理、超时、重启策略、日志、信号处理、跨平台差异（Windows 没有 fork、信号处理不同）。
4. 它可以在不写任何产品代码的情况下完成——只需要写一个最小可运行的 hello-world App 和 Core 的 App host 原型。

**具体动作：** 在 5 个工作日内，写出 Process contract 的初稿，包含：

- App 启动命令格式
- Token 传递方式（环境变量或 stdin）
- 健康检查协议（HTTP 路径、超时、重试）
- 退出码语义
- stdout/stderr 约定
- 崩溃检测和重启策略
- 一个最小可运行的伪代码示例

然后用一个 hello-world App 验证这个 contract 在 Linux、macOS、Windows 上都能工作。

---

## 9. 结论

**应该按这个契约继续，但有一个前提条件：M0 必须完成所有 P0 项的解决，否则不应进入实现阶段。**

这个契约的方向是对的。Core 收缩为本地优先运行时、App 承载领域模型、分发以 Report 为入口、更新通道分离——这些判断在 2026 年的本地优先软件生态中是合理的。契约的作者表现出了良好的克制力：没有把 Core 做成一个万能平台，没有把 TAA 塞进 Core，没有在 v0 引入账号系统。

但契约目前是"意图声明"而非"工程规格"。从意图到实现之间，缺少的是协议细节和失败语义。软件架构的失败很少是因为方向错误，更多是因为边界条件没有定义清楚。App 崩溃了怎么办？签名密钥泄露了怎么办？备份文件损坏了怎么办？这些问题的答案必须在写第一行产品代码之前确定。

**如果 M0 结束时 P0 项仍未解决，替代方案是：** 放弃 Core + Apps 分离架构，回到单体应用模式（beta.28 的延续），将 Report 和 Project 作为同一代码库中的模块。这不是更好的架构，但如果团队没有能力在 M0 内解决进程边界、签名体系、数据分层这三个问题，单体模式至少是可控的。分离架构的复杂度是真实的，如果做不好，比单体更糟。