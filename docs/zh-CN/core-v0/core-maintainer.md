# Core v0 维护者指南

- 读者：`loomsci_core` 维护者
- 状态：preview；`core/1`
- 测试：`python -m unittest discover -s tests -q`

## 1. 目录

```text
loomsci_core/          正式 Core 包
├─ store.py            SQLite items/tags/blobs/apps/FTS
├─ server.py           Flask API 与鉴权
├─ app_host.py         App 进程与 scoped token
├─ backup.py           数据型备份/恢复
├─ cli.py              start/stop/status/doctor
├─ sdk.py              公共 SDK
├─ version.py          版本/API 常量
└─ __main__.py         python -m loomsci_core

examples/hello-app/    SDK 参考 App
prototype/             非产品研究/原型
tests/                 现有产品 + 正式包测试
docs/                  契约与指南
```

`prototype/` 不是产品，不能交付，也不能让 App 开发者依赖它。

## 2. 数据

```text
<home>/data/core.db
<home>/data/blobs/
<home>/apps/<slug>/data/
<home>/local.token
```

- items/tags/blobs/apps/items_fts 属于 Core
- App data 属于 App
- 不把 App 专用表塞进 Core
- FTS 是派生数据，可从 items 重建

## 3. API 变更

`core/1` 只做加法。

允许：

- 新可选字段
- 新端点
- 新响应字段

没有 `core/2` 不允许：

- 删除/重命名字段
- 改变 item/blob 身份
- 改变 backup 格式
- 改变 App 生命周期
- 改变 token 语义

App 专用需求推回 App 层。

## 4. App 隔离

- scoped token 映射 token -> app slug
- App token 不能读其他 App
- v0 没有 `items.cross_read`
- App code/venv 不进数据备份
- App update/remove 保留 `apps/<slug>/data/`

## 5. 备份

数据型：

```text
data/core.db
data/blobs/
apps/<slug>/data/
apps/installed.json
manifest.json
```

排除：token、logs、venv、code、cache。

恢复目标必须为空；token 重新生成。

## 6. Updater

原型链：

```text
verify signed package
→ backup
→ stop Core
→ atomic payload replace
→ start
→ health
→ rollback on failure
```

当前 payload 是 marker；完整包替换仍未做。

## 7. 测试

```bash
python -m unittest discover -s tests -q
python -m unittest tests.test_loomsci_core -v
python -m unittest tests.test_loomsci_core_sdk -v
python prototype/test_core_m1.py
```

平台矩阵：macOS + Windows。Linux 后续。

## 8. 发布检查（C1 前）

- [ ] 测试全绿
- [ ] API 文档/OpenAPI 更新
- [ ] manifest/SDK 示例更新
- [ ] backup/restore 通过
- [ ] migration dry-run/apply 通过
- [ ] signed updater 通过
- [ ] macOS 安装/启动
- [ ] Windows 安装/启动
- [ ] 公共树无私有路径/密钥
- [ ] 版本与 changelog 更新
- [ ] 回滚 tag

## 9. 安全

- 只绑定 loopback
- local token 0600
- App token scoped
- 无跨 App 读
- 解压前验签
- 日志无密钥
- 无任意 App-to-App RPC

## 10. 迁移

beta.28 -> v0：

- 源只读
- 新工作区
- posts -> items
- attachments -> blobs
- facts -> project.fact items
- projects/tasks -> Project DB
- summaries/mentions/reads -> legacy archive
- 切换前校验计数/hash

## 11. 已知缺口

- 完整包 updater
- 干净安装器
- OpenAPI 生成 SDK
- conformance suite
- App CLI 命令
- 外部 demo App
- 30 天无 breaking 窗口
- C1 评审
