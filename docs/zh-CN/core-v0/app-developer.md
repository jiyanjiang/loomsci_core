# Core v0 App 开发者指南

- 读者：基于 `core/1` 开发 App 的开发者
- 状态：preview；App API 为 `app/1`
- 参考 App：`examples/hello-app`
- SDK：`loomsci_core.sdk.CoreClient`

## 1. App 拥有什么

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
backup
```

## 2. 最小目录

```text
my-app/
├─ manifest.json
└─ my_app/
   ├─ __init__.py
   └─ server.py
```

`manifest.json`：

```json
{
  "name": "My App",
  "slug": "my-app",
  "version": "0.1.0",
  "package": "my_app",
  "entry": "server",
  "health": "/health",
  "permissions": ["items.read", "items.write"]
}
```

## 3. 进程契约

Core 启动：

```text
<app-venv>/python -m <package>.<entry>
```

环境变量：

```text
LOOMSCI_CORE_URL
LOOMSCI_APP_TOKEN
LOOMSCI_APP_SLUG
LOOMSCI_APP_PORT
LOOMSCI_APP_DATA_DIR
LOOMSCI_APP_LOG_DIR
```

App 必须：

- 监听 `127.0.0.1:LOOMSCI_APP_PORT`
- 提供 `GET /health`，返回 200 + `{"ok":true}`
- 收到终止信号后退出
- 不 fork 常驻 daemon
- 不把 token 写日志

## 4. SDK

```python
from loomsci_core.sdk import CoreClient

client = CoreClient(
    os.environ["LOOMSCI_CORE_URL"],
    os.environ["LOOMSCI_APP_TOKEN"],
)

item = client.create_item(
    app="my-app",
    type="my-app.note",
    title="Hello",
    body="Markdown",
    tags=["demo"],
)
print(client.search("Hello"))
```

SDK 方法：

```text
health
create_item / get_item / list_items / update_item / delete_item
set_tags / list_tags
search
upload_blob / download_blob
```

不要 import `loomsci_core.store`、`app_host`、`server`、`backup`。这些是 Core 内部实现。

## 5. Scoped 访问

App token 只能访问自己的 `app` namespace：

- create item：`app` 必须等于 manifest slug
- list/get/update/delete：只能自己的 item
- search/tags：只搜自己的 namespace
- backup/App 管理：禁止

v0 没有跨 App 读。

## 6. 安装与运行

当前 preview 用 API：

```bash
python -m loomsci_core --home /tmp/core --port 8795 start
TOKEN=$(cat /tmp/core/local.token)

curl -sS -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"source":"/absolute/path/to/my-app"}' \
  http://127.0.0.1:8795/v1/apps/install

curl -sS -H "Authorization: Bearer $TOKEN" \
  -X POST http://127.0.0.1:8795/v1/apps/my-app/start
```

当前 preview 还没有完整的 `loomsci app ...` CLI 辅助命令。

## 7. App 数据

```text
<home>/apps/my-app/data/
```

- Core 会保留；本版本没有 update/remove 命令
- 备份包含 App data，不包含 code/venv
- App 自己负责数据迁移

## 8. 示例

`examples/hello-app` 用 SDK 写 item：

```text
POST /write
→ CoreClient.create_item()
→ Core /v1/items
```

测试：

```bash
python -m unittest tests.test_loomsci_core_sdk
```

## 9. 规则

- 只用 `/v1` 或 SDK
- 不读其他 App 数据
- 不写自己 data 目录之外
- 不依赖 Core 内部模块
- Core 不在时优雅失败，不静默崩溃
- 日志不含密钥
- `core_api` 不兼容时明确报错

## 10. 已知缺口

- 没有第三方 App 市场
- 没有 App CLI 命令
- 没有生产签名包布局
- 没有跨 App 共享
- 没有多用户身份
- 没有自动 App 迁移
