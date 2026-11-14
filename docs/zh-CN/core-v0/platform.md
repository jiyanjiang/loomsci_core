# LoomSci Core v0.1 · 平台说明

- 状态：**App Platform Preview**，不是稳定公开 SDK
- 版本：`0.1.0`
- API：`core/1`
- App API：`app/1`
- Python：3.12
- 平台：macOS + Windows（主要测试目标）

## 1. Core 是什么

LoomSci Core 是面向 AI 原生应用的本地优先运行时。

```text
Core = 工作区 + items + blobs + tags + search + App Host + backup + updater
App  = 领域模型 + UI + 工作流 + 内容
```

Core 不需要账号。绑定 `127.0.0.1`，数据在本地工作区，给 App 稳定的 HTTP/SDK 接口。

Core 不是：

- 聊天 UI
- 多用户服务器
- 任务/Agent 调度器
- 云同步服务
- 报告/项目/写作产品

这些属于 App。

## 2. 安装与运行

从仓库：

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-core.txt
./.venv/bin/python -m loomsci_core --home /tmp/loomsci-core --port 8795 start
./.venv/bin/python -m loomsci_core --home /tmp/loomsci-core status
./.venv/bin/python -m loomsci_core --home /tmp/loomsci-core stop
```

`pyproject.toml` 也定义了 `loomsci-v0` 命令。

## 3. 工作区

```text
<home>/
├─ data/
│  ├─ core.db
│  └─ blobs/
├─ apps/<slug>/
│  ├─ manifest.json
│  ├─ code/
│  ├─ venv/
│  └─ data/
├─ backups/
├─ logs/
├─ runtime/core.json
└─ local.token
```

`local.token` 权限必须是 `0600`，不能提交。

## 4. 本地安全

```text
Authorization: Bearer <local.token>
```

- `/v1/health` 与 `/v1/version` 公开
- 其他端点需要 master token 或 scoped app token
- App token 只能访问自己的 `app` namespace
- v0 不提供跨 App 读
- 不需要用户账号或云身份

## 5. 概念

### Item

通用可读记录：

```json
{
  "id": "i-...",
  "app": "report",
  "type": "report.note",
  "title": "PISA",
  "body": "Markdown body",
  "metadata": {},
  "tags": [{"tag": "pisa", "source": "ai", "confidence": null}]
}
```

`type` 由 App 定义，约定 `<app>.<type>`。

### Blob

关联到 item 的二进制附件，存放在 `data/blobs/`。

### App

由 Core 管理的独立版本进程，使用 `app/1` manifest 和 scoped token。

### Backup

数据型备份：core DB、blobs、App data、installed metadata。排除代码/venv/token。

## 6. API 与 SDK

API 参考：[core-api](core-api.md)  
OpenAPI：[openapi.json](../../openapi/core-v0.json)  
SDK：`loomsci_core.sdk.CoreClient`

```python
from loomsci_core.sdk import CoreClient

client = CoreClient("http://127.0.0.1:8795", token)
item = client.create_item(app="my-app", type="my-app.note", title="Hello", body="World")
print(client.search("Hello"))
```

## 7. App 开发

阅读 [app-developer](app-developer.md)。  
Core 维护者指南：[core-maintainer](core-maintainer.md)。

第一个参考 App：`examples/hello-app`。

## 8. 当前限制

这是 **preview**：

- 没有生产安装器
- 没有 OpenAPI 生成客户端
- 没有第三方 App 市场
- 没有多用户/账号
- 没有跨 App 读
- App CLI 辅助命令未完整
- 签名/updater 仍是原型
- 没有云同步

不要向最终用户承诺生产稳定性。

## 9. 版本策略

```text
core/1   v0.x 内只做加法
app/1    App manifest 契约
```

破坏性变更需要新 major（`core/2`）和迁移计划。
