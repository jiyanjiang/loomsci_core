# Core v0 API 参考

- Base URL：`http://127.0.0.1:<port>`
- API：`core/1`
- 鉴权：`Authorization: Bearer <token>`
- 公开：`/v1/health`、`/v1/version`
- 写操作只接受 JSON

## 错误格式

```json
{"ok": false, "error": "error_code"}
```

| 错误 | HTTP | 含义 |
|---|---:|---|
| `unauthorized` | 401 | 缺 token / token 错 |
| `json_required` | 400 | body 不是 JSON object |
| `invalid app` / `invalid type` | 400 | app/type slug 非法 |
| `not_found` | 404 | item/blob/app 不存在 |
| `forbidden` | 403 | scoped app 越权 |
| `tags_required` | 400 | tags 必须是 list |
| `target_exists` | 400 | 恢复目标已存在 |
| `backup_*` / `hash_mismatch` | 400 | 备份校验失败 |

## Health / version

### GET `/v1/health`

```json
{"ok": true, "api": "core/1", "schema": 1, "service": "core_v0"}
```

### GET `/v1/version`

```json
{"ok": true, "product": "loomsci_core", "version": "0.1.0", "api": "core/1"}
```

## Items

### POST `/v1/items`

```json
{
  "app": "report",
  "type": "report.note",
  "title": "PISA",
  "body": "# Markdown",
  "metadata": {"style": "research-perspective-0.1.0"},
  "tags": ["pisa", "science"],
  "id": "optional-caller-id"
}
```

- `title`/`body`/`metadata`/`tags` 可选
- `id` 可选，必须唯一
- `app`/`type` 必填
- 最多 8 个标签，自动小写归一

响应 `201`：

```json
{"ok": true, "item": {
  "id": "i-...", "app": "report", "type": "report.note",
  "title": "PISA", "body": "# Markdown", "metadata": {},
  "tags": [{"tag": "pisa", "source": "ai", "confidence": null}],
  "created_at": "...", "updated_at": "..."
}}
```

### GET `/v1/items`

Query：

```text
app, type, tag, limit (1..200), offset
```

### GET `/v1/items/<id>`

### PATCH `/v1/items/<id>`

允许字段：`title`、`body`、`metadata`。

### DELETE `/v1/items/<id>`

### POST `/v1/items/<id>/tags`

```json
{"tags": ["a", "b"], "source": "ai"}
```

替换标签。

### GET `/v1/tags?limit=100`

```json
{"ok": true, "tags": [{"tag": "pisa", "count": 3}]}
```

### GET `/v1/search?q=PISA&limit=50`

对 title/body/tags/app 做 FTS。scoped app 只搜自己的 app。

## Blobs

### POST `/v1/blobs`

```json
{
  "filename": "report.md",
  "content_type": "text/markdown",
  "content_base64": "IyBoZWxsbw==",
  "item_id": "i-..."
}
```

### GET `/v1/blobs/<id>`

返回字节，`Content-Disposition: attachment`。

### GET `/v1/blobs/<id>?inline=1`

返回 JSON 文本（最多 200,000 字符）和 `truncated`。

## Backups

### GET `/v1/backups`

列出带 manifest 的备份目录。

### POST `/v1/backups`

在 `<home>/backups/` 创建数据备份，返回 `{name,path}`。

### POST `/v1/backups/restore`

```json
{"backup": "/path/to/backup", "target": "/path/to/new-home"}
```

- target 必须不存在
- 复制前校验 hash
- token 重新生成
- 不恢复 App code/venv

## Apps

### GET `/v1/apps`

### POST `/v1/apps/install`

```json
{"source": "/path/to/app"}
```

### POST `/v1/apps/<slug>/start`

### POST `/v1/apps/<slug>/stop`


## Scoped app token

App 从环境获得 `LOOMSCI_APP_TOKEN` 与 `LOOMSCI_CORE_URL`，用
`Authorization: Bearer` 调用 Core。

scoped token：

- 只能创建自己 `app` 的 item
- 只能 list/get/update/delete 自己 app 的 item
- 只能搜索/打标签自己的 namespace
- 不能用 backup 与 App 管理端点
