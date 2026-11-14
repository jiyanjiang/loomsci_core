# Core v0 维护者指南

- 读者：`loomsci_core` 维护者
- 状态：最小版 `0.1.0`；API `core/1`
- 测试：`python -m unittest discover -s tests -q`

## 1. 仓库结构

```text
loomsci_core/
├─ store.py       SQLite items/tags/blobs/apps/FTS
├─ server.py      Flask API 与鉴权
├─ app_host.py    App 安装/启动/停止与 scoped token
├─ backup.py      数据备份/恢复
├─ cli.py         start/stop/status
├─ sdk.py         公开 SDK
├─ version.py     版本/API 常量
└─ __main__.py    python -m loomsci_core

examples/hello-app/  SDK 参考 App
tests/               Core 与 SDK 测试
docs/                最小平台/API/App/维护者文档
```

## 2. 数据

```text
<home>/data/core.db
<home>/data/blobs/
<home>/apps/<slug>/data/
<home>/local.token
```

- items/tags/blobs/apps/items_fts 属于 Core。
- App data 属于 App。
- 不把 App 专用表塞进 Core。
- FTS 是派生数据，可从 items 重建。

## 3. API 规则

`core/1` 只做加法。

允许：

- 新增可选字段
- 新增端点
- 新增响应字段

没有 `core/2` 不允许：

- 删除/重命名字段
- 改 item/blob 身份
- 改备份格式
- 改 App 生命周期
- 改 token 语义

App 专用需求留在 App。

## 4. App 隔离

- scoped token 映射到 App slug。
- App token 不能读其他 App。
- v0 没有跨 App 读取。
- App code/venv 不进数据备份。
- App data 在 `apps/<slug>/data/`。

## 5. 备份

只备份数据：

```text
data/core.db
data/blobs/
apps/<slug>/data/
apps/installed.json
manifest.json
```

不包含 token、日志、venv、code、cache。
恢复要求目标为空；token 会重新生成。

## 6. 测试

```bash
python -m unittest discover -s tests -q
python -m unittest tests.test_loomsci_core -v
python -m unittest tests.test_loomsci_core_sdk -v
```

目标平台：macOS 与 Windows。

## 7. 发布检查

- [ ] 测试全绿
- [ ] API 文档与 OpenAPI 更新
- [ ] example app 可运行
- [ ] backup/restore 通过
- [ ] macOS start/stop
- [ ] Windows start/stop
- [ ] 公共树无私有路径、token、key
- [ ] `VERSION`、`pyproject.toml`、`loomsci_core.version` 一致
- [ ] tag 与 release notes

## 8. 安全

- 只绑 loopback
- local token 权限 `0600`
- app token 限 scope
- 无跨 App 读取
- 日志无 secret
- 无 App-to-App RPC

## 9. 不在本版本范围

- installer、updater、签名包
- App update/remove 命令
- 迁移工具
- App 市场
- 外部账号/多用户
- 云同步
- 第三方 App conformance
