# Core 平台契约 · v0

- 状态：草案，2026-11-14
- 取代：`core-contract.md` v1（beta 时期的应用契约）
- 适用：未来的 `loomsci_core` 分发版，不适用于当前的 `0.1.0-beta.28`
- 产品形态：**LoomSci Core + Specific APP**
- TAA：先锋实验平台，不是 Core 代码库

## 1. Core 是什么

Core 是 LoomSci 应用可以依赖的最小、稳定、本地优先运行时。它不是完整产品功能集。

```text
LoomSci Core = 工作区 + 存储 + 搜索 + 本地 API + App Host + 更新器
LoomSci App  = 领域模型 + UI + 工作流 + 内容
```

Core 在没有任何 App 时也必须可用：

- 启动和停止
- 存通用 item 和 blob
- 标签与搜索
- 备份、恢复、导出
- 安装、启动、停止、更新 App

Core 不得要求注册或联网。

## 2. 硬保证

1. **默认本地**：仅监听 loopback。Core 不做账号、登录、云、遥测。
2. **Core 独立可用**：不装任何 App 也能存、搜、导出、备份。
3. **稳定 App API**：App 面向 `core/1`；同一主版本内只做加法。
4. **App 隔离**：每个 App 有独立包、数据命名空间、端口、健康路径。Core 不 import App 代码。
5. **用户拥有数据**：本地工作区；导出/备份是一等功能，不是付费功能。
6. **签名分发**：Core、App、内容包在安装/使用前都要校验。
7. **更新通道分离**：软件更新、App 更新、内容更新、权益更新是不同操作。
8. **不强制账号**：免费本地使用永远不需要注册。

## 3. 分层

```text
Core process
├─ Workspace layout
├─ SQLite + blob store
├─ Generic items / tags / search
├─ Local HTTP API + capability token
├─ App host
├─ Backup / restore / export / import
├─ Software updater
└─ Minimal web shell
        │
        ├─ Report app
        ├─ Project app
        └─ future apps
```

最小 Web 壳只做诊断、App 启动器、更新状态、通用 item 阅读。不得变成领域应用。

## 4. 工作区布局

```text
~/.loomsci/
├─ core/                 # Core 代码或安装运行时
├─ data/
│  ├─ core.db            # items, tags, apps, events
│  └─ blobs/             # 内容寻址附件
├─ apps/
│  └─ <slug>/
│     ├─ manifest.json
│     ├─ code/
│     └─ data/           # App 命名空间，默认保留
├─ config.yaml
├─ logs/
├─ backups/
└─ runtime/
```

路径属于稳定契约。App 不得越界写文件，只能走 Core API。

## 5. Core 数据模型

Core 只拥有通用原语：

```text
items
  id, app, type, title, body, metadata_json, created_at, updated_at

item_tags
  item_id, tag, source, confidence

blobs
  id, item_id, filename, content_type, bytes, sha256, created_at

apps
  slug, version, manifest_json, installed_at

events
  id, app, kind, payload_json, created_at
```

App 领域表放在 App 命名空间，不进 Core 表。

Core 对 `items.title`、`items.body`、`item_tags.tag`、`items.app` 建 FTS5。App 可建自己的索引，但不能替换 Core 搜索。

## 6. HTTP API

```text
GET    /v1/health
GET    /v1/version
GET    /v1/status

POST   /v1/items
GET    /v1/items
GET    /v1/items/<id>
PATCH  /v1/items/<id>
DELETE /v1/items/<id>

POST   /v1/items/<id>/tags
GET    /v1/tags
GET    /v1/search

POST   /v1/blobs
GET    /v1/blobs/<id>
GET    /v1/blobs/<id>/inline

GET    /v1/apps
POST   /v1/apps/install
POST   /v1/apps/<slug>/start
POST   /v1/apps/<slug>/stop
POST   /v1/apps/<slug>/update
POST   /v1/apps/<slug>/remove

GET    /v1/updates/status
POST   /v1/updates/check
POST   /v1/updates/apply

GET    /v1/backup
POST   /v1/backup
POST   /v1/restore
```

App 只能走 `/v1`，不得 import Core 内部模块。

## 7. 本机能力令牌

Core 不做用户账号，但需要本机 capability token，防止其他本地页面/进程随意调用 API。

```text
~/.loomsci/local.token   # 0600
```

- CLI 自动读取
- Web 壳通过同源会话获取
- App 从 App Host 获取 scoped token
- 它不是用户身份，不发送给第三方
- 丢失可轮换，App 需重新注册

这是安全边界，不是注册。

## 8. App Host 职责

- 校验 manifest 和签名
- 检查 `core_api`、`min_core`、`max_core`
- 分配/校验 loopback 端口
- 创建数据命名空间
- 启动/停止/健康检查
- 下发 scoped token
- 更新时保留 App 数据
- 卸载代码但默认保留数据
- App 错误不得拖垮 Core

## 9. 更新通道

```text
core-software     签名 Core 二进制/包
app-software      签名 App 包
content           签名数据包，不能执行代码
entitlement       签名授权/积分，App 层处理
```

规则：

- 内容包不能执行代码
- 软件与内容版本独立
- 更新失败回滚
- 离线保留最后可用状态
- Core 永不成为计费/授权服务器

## 10. 明确不做

- 用户账号、登录、多用户、团队
- 聊天、房间、社交 feed、评论
- 任务派发、执行器、agent 调度
- 联邦、对等同步、隧道、发现
- 插件市场
- Core 内模型调用
- 计费、积分、订阅
- 内容生成

这些属于 App 或 TAA。

## 11. 兼容与迁移

- API 版本：`core/1`
- App manifest：`app/1`
- schema 迁移只做加法；破坏性变更需要 Core 新主版本
- `0.1.0-beta.28` 是旧实现，尚未满足 Core v0
- 迁移：
  1. 盘点 `posts` / `tasks` / `facts` / `projects`
  2. posts/attachments → `items` + `blobs`
  3. 领域表移入 Report / Project App
  4. 至少保留一个版本的导出/备份兼容
  5. 通过 export/restore 测试后再删旧表

## 12. Core v0 验收

1. 干净机器无需 Python 知识即可安装
2. `loomsci start` 离线可用，`/v1/health` 正常
3. Markdown + blob 经重启、备份、恢复不丢
4. 按正文、标题、标签、App 搜索
5. App 可安装、启动、停止、更新、卸载
6. App 更新保留数据；Core 不受 App 卸载影响
7. 内容包可应用、可回滚
8. 损坏包拒绝并给出清晰错误
9. 所有本地功能无需注册
10. App 不能越权读另一个 App 命名空间

## 13. 待定

- 运行时：打包 Python 还是原生二进制
- 浏览器/App 的 token 传输方式
- App 间共享走 Core items 还是 App API
- Core 内置多少通用阅读 UI
- 首个公开版支持哪些 OS
