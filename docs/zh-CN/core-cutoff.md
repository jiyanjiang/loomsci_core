# Core 阶段性截止点 · v0

- 日期：2026-11-14
- 目的：定义 Core 何时稳定到可以独立开发 App，包括交给其他人开发
- 规则：不允许外部开发者直接基于 M1 原型代码开始

## 1. 截止点

```text
C0  M1 端到端原型            内部使用，不是平台
C1  Core v0.1 App Platform Preview  第一批外部 App 开发者
C2  Core v1.0 Stable         公开 App 平台
C3  Core maintenance         只修 bug/安全
```

**真正的截止点是 C1。**  
C1 时冻结 `core/1` 与 `app/1`，App 进入独立仓库；Core 停止功能扩张，只接受 bug/安全/加法变更。

## 2. C0 · M1 端到端

当前：

```text
items / tags / blobs / search
App Host + scoped app token
backup / restore
migration apply
CLI start/stop/status
迁移工作区可加载
macOS PASS, Windows PASS
```

C0 是原型，不是 SDK，不能交给外部 App 开发者。

C0 退出条件：

- M1 在 macOS + Windows 通过
- demo app 用 scoped token 跑通
- backup/restore 与 migration apply 通过
- 所有 `prototype/` 代码标记为非产品

## 3. C1 · Core v0.1 App Platform Preview

这是**允许其他 App 开始开发**的截止点。

### 必须交付

1. **Core runtime**
   - 正式 `core` 包/入口，不再是 `prototype/core_v0`
   - CLI：`start`、`stop`、`status`、`doctor`、`app`、`backup`
   - local token 与 scoped app token
2. **冻结契约**
   - `core/1` API
   - `app/1` manifest
   - workspace 布局
   - items/tags/blobs schema
   - backup 格式
   - App 生命周期
3. **App SDK**
   - 至少 Python SDK
   - App template
   - 独立目录/仓库的 example app
   - manifest validator
4. **API 文档**
   - OpenAPI 或等价端点参考
   - 错误码
   - 权限表
5. **分发**
   - 签名 Core 包
   - 签名 App 包格式
   - updater + backup/rollback
   - macOS + Windows 干净安装
6. **一致性测试**
   - Core contract tests
   - SDK tests
   - example app 双机生命周期
7. **交接文档**
   - `app-developer.md`
   - `core-maintainer.md`
   - 发布/版本策略
   - 安全策略

### C1 验收

```text
1. 干净 macOS 安装 + 启动
2. 干净 Windows 安装 + 启动
3. SDK 读写 items/blobs/search
4. example app install/start/stop/update/remove
5. scoped app 读不到其他 app
6. backup/restore
7. 签名包验证 + 回滚
8. beta.28 迁移工作区可打开
9. 2–3 名受信外部开发者不改 Core 就能做出 demo app
10. 连续 30 天没有 breaking core/1 变更
```

如果 2–3 个外部 App 必须改 Core 才能做出来，C1 未达成。

## 4. C2 · Core v1.0 Stable

C2 在真实 App 开发之后，不是之前。

必须有：

- 至少 3 个 Core 外部 App，来自至少 2 个 owner
- 这些 App 不需要改 Core 源码
- `core/1` 连续 90 天无 breaking 或仅加法
- backup/restore/migration 在真实工作区验证
- updater/rollback 双机验证
- 外部开发者用 public template + SDK 独立跑通
- local token、App 隔离、包验证安全评审

C2 可以改：

- 文档、打包、性能、bug 修复
- 加法 API
- SDK 易用性

C2 不能无 major 改：

- `core/1` breaking shape
- item/blob/tag 身份
- backup 格式
- App manifest 语义
- App 生命周期语义

## 5. C3 · 维护模式

C2 之后：

- Core 只接受 bug/安全修复和加法 API
- 新领域功能进 App
- breaking 变更需要 `core/2` 与迁移计划
- 新 App 不再等 Core 发版

## 6. C1 后 App 开发者可以做什么

```text
LoomSci Report
LoomSci Monograph
LoomSci Project
科学传播
小说 / 长文写作
政策简报
领域阅读器
```

App 拥有：

```text
领域 schema
UI
工作流
内容
可选账号/付费
```

App 不拥有：

```text
Core DB
Core token
App Host
backup/update
```

## 7. C1 时 Core 必须停止什么

- 不再往 Core 加领域功能
- 不再加 Report/Project 专用表
- 不再为某个 App 加专用 UI
- 不再为单个 App 增加 Core 类型
- 不做静默 API 变更

新 App 需求先走 App 层。只有通用、可复用的能力才进 Core，并且只能加法发布。

## 8. 交接包

邀请其他开发者前：

```text
loomsci_core/
├─ core/
├─ sdk/python/
├─ examples/hello-app/
├─ docs/
│  ├─ app-developer.md
│  ├─ core-maintainer.md
│  ├─ core-contract.md
│  ├─ app-manifest.md
│  └─ release.md
├─ tests/
│  ├─ contract/
│  └─ conformance/
└─ scripts/
   ├─ app-test
   └─ package
```

App 开发者应该能：

```bash
loomsci app init my-app
loomsci app test ./my-app
loomsci app install ./my-app
```

不需要读 Core internals。

## 9. 当前到 C1 的差距

```text
[ ] prototype 移入正式 core
[x] SDK + App template
[ ] OpenAPI/API reference
[ ] 签名 Core/App 包集成
[ ] updater + rollback
[ ] macOS/Windows 干净安装器
[ ] conformance suite
[ ] App 开发者交接文档
[ ] 2–3 个外部 demo app
[ ] 30 天无 breaking 窗口
```

## 10. 决定

**截止点 = C1 Core v0.1 App Platform Preview。**

到那时：

- Core 停止功能开发
- App 进入独立仓库
- 其他人可以基于 `core/1` + `app/1` 开发
- Core 只做修复、硬化、加法扩展
- C2/v1.0 由外部 App 的真实使用挣得，而不是提前宣布
