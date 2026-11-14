# App manifest 契约 · v0

- 状态：草案，2026-11-14
- API：`app/1`
- Core API：`core/1`
- 适用：LoomSci Core 之上分发的 App

## 1. 原则

App 是独立版本的产品，依赖 Core，不重写 Core。

```text
Core 管：工作区、items、blobs、tags、search、App 生命周期、备份、更新
App 管：领域 schema、领域 UI、工作流、内容、可选账号
```

## 2. Manifest 示例

```json
{
  "name": "LoomSci Report",
  "slug": "report",
  "version": "0.1.0",
  "app_api": "app/1",
  "core_api": "core/1",
  "min_core": "0.2.0",
  "max_core": "0.9.99",
  "package": "loomsci_report",
  "entry": "server",
  "port": 8791,
  "health": "/health",
  "data_namespace": "app_report",
  "permissions": [
    "items.read", "items.write", "blobs.read", "blobs.write",
    "tags.write", "search.read"
  ],
  "update_channels": ["stable", "beta"],
  "content_channels": ["daily"],
  "preserve": ["data"],
  "uninstall": "keep_data",
  "requires_registration": false
}
```

## 3. 必填字段

| 字段 | 类型 | 规则 |
|---|---|---|
| `name` | string | 可读名称 |
| `slug` | string | 小写 `[a-z0-9-]`，唯一 |
| `version` | semver | App 版本 |
| `app_api` | string | `app/1` |
| `core_api` | string | `core/1` |
| `min_core` | semver | 最低 Core |
| `max_core` | semver | 可选上限 |
| `package` | string | 可导入目录名 |
| `entry` | string | 包内模块 |
| `port` | int | loopback 端口；`0` 由 Core 分配 |
| `health` | string | HTTP 健康路径 |
| `data_namespace` | string | 隔离命名空间 |
| `permissions` | array | 申请的 Core 能力 |
| `update_channels` | array | 软件更新通道 |
| `content_channels` | array | 内容通道 |
| `preserve` | array | `data` / `config` / `none` |
| `uninstall` | string | `keep_data` / `remove_data` |
| `requires_registration` | bool | 仅 App 层；Core 永不要求 |

## 4. 可选字段

`description` `homepage` `license` `icon` `min_os` `screenshots`
`capabilities` `default_profile` `compatibility`

## 5. 权限

| 权限 | 含义 |
|---|---|
| `items.read` | 读本 App 命名空间的 items |
| `items.write` | 增删改本 App items |
| `items.cross_read` | 读其他 App items（需显式批准） |
| `blobs.read` | 读本 App 附件 |
| `blobs.write` | 给本 App items 挂附件 |
| `tags.read` | 读标签 |
| `tags.write` | 增删标签 |
| `search.read` | 用 Core FTS |
| `apps.list` | 列已安装 App |
| `content.read` | 安装签名内容包 |
| `update.self` | 自更新 |

默认无权限；只申请需要的。

## 6. 生命周期

```text
install
  validate manifest
  validate signature/checksum
  check core_api + min_core/max_core
  create data namespace
  copy code
  register in Core apps

start
  allocate/verify port
  launch entry with scoped token
  wait for health
  mark running

stop
  graceful shutdown
  preserve data

update
  stop if running
  backup code/data
  verify new package
  replace code, preserve data
  start + health check
  rollback on failure

remove
  stop
  remove code
  keep data by default
  explicit remove_data only with confirmation
```

## 7. Bootstrap 安装器

Report 是大多数用户的入口。

```text
Report installer
  ├─ detect Core
  │   ├─ binary on PATH
  │   ├─ workspace metadata
  │   └─ /v1/health
  ├─ if missing:
  │   download signed Core
  │   verify sha256 + signature
  │   install Core
  ├─ verify core_api
  ├─ install Report
  └─ start Core + Report; open local UI
```

规则：

- Core 只装一次，不创建重复工作区
- 不静默覆盖已有 Core
- 卸载 Report 保留 Core 和用户数据
- 支持离线安装包
- 安装过程不要求注册

## 8. 内容包

内容与软件分离：

```json
{
  "kind": "content",
  "app": "report",
  "channel": "daily",
  "version": "2026-11-14",
  "items": [{"id": "...", "title": "...", "summary": "...", "tags": ["..."]}],
  "sha256": "...",
  "signature": "...",
  "license": "free"
}
```

规则：

- 内容包不能含可执行代码
- 本地缓存
- 失败保留上一版
- 付费内容由 App entitlement 控制，Core 不注册
- 内容更新不得阻塞 Core 启动

## 9. 兼容

- `app_api` 与 `core_api` 独立
- `min_core` / `max_core` 决定能否安装
- 不兼容时 Core 给出诊断
- Core `core/1` 内只做加法
- App 数据库迁移由 App 自己负责，只做加法

## 10. 示例 App

### Report

```text
app/report
own: reports, sources, evidence, daily content, reading UI
use: items, blobs, tags, search
```

### Project

```text
app/project
own: projects, tasks, decisions, agent roles, handoffs, reviews
use: items, blobs, tags, search
```

Project 不执行 agent，只记录项目状态；执行在 AI IDE。

## 11. 验收

1. Report 可在干净机器安装，缺 Core 时自动安装
2. 不注册也能用全部本地 Report 功能
3. App 更新保留 App/Core 数据
4. App 卸载默认保留数据
5. 签名内容包可离线应用、回滚
6. 无权限 App 不能读其他命名空间
7. Core 版本不满足 `min_core`/`max_core` 时明确拒绝
8. 签名无效时在复制代码前拒绝

## 12. 非目标

- v0 第三方 App 市场
- App 间任意 RPC
- Core 内 App 计费
- App 自有用户身份
- 内容包执行代码
- App 要求管理员权限
