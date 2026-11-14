# beta.28 → Core v0 迁移计划

- 状态：M0 草案，2026-11-14
- 源：`0.1.0-beta.28` SQLite 工作区
- 目标：Core v0 工作区 + Report/Project App 数据库
- 模式：安全迁移；源只读；先写新工作区
- 平台：macOS 与 Windows

## 1. 原则

beta.28 工作区**绝不原地修改**。迁移工具只读源，写新工作区，校验计数和 hash，用户确认后才切换。

```text
beta.28 工作区（只读）
→ 临时 Core v0 工作区
→ Report DB / Project DB
→ legacy archive
→ 校验
→ 原子切换（可选）
```

任何失败，源工作区仍可用。

## 2. 当前数据量

A 机 beta.28：

```text
posts                 48
post_summaries         8
tasks                  4
facts                  1
attachments           13
mentions               1
reads                  1
presence               1
projects               1
project_sources        1
project_entries     3,586
project_schemas        3
project_apps           1
project_evaluations    1
tags                   0
post_tags              0
tag_aliases            0
```

迁移必须按实际计数校验，不能硬编码。

## 3. 目标归属

| beta.28 | 目标 | 规则 |
|---|---|---|
| `posts` | Core `items` | type `report.note`；保留 id/body/meta |
| `attachments` | Core `blobs` | 保留 id、filename、content_type、sha256、bytes |
| `post_tags` / `tags` | Core `item_tags` | 保留名称/source |
| `facts` | Core `items` | type `project.fact`；metadata 保留字段 |
| `projects` | Project App DB + Core 投影 | `project.project` item |
| `project_sources` | Project App DB | 引用 project id |
| `project_entries` | Project App DB | 批量插入 3,586 行 |
| `project_schemas` | Project App DB | 引用 project id |
| `project_apps` | Project App DB | 引用 project id |
| `project_evaluations` | Project App DB | 引用 project id |
| `tasks` | Project App DB | 可选 `project.task` 投影 |
| `mentions` | legacy archive | 不迁移 |
| `reads` | legacy archive | 阅读状态可重建 |
| `presence` | legacy archive | 临时状态 |
| `post_summaries` | legacy archive | **不迁移** |
| `tag_aliases` | legacy archive | App 可重建 |
| FTS 表 | 重建 | 派生数据，不复制 |
| `schema_migrations` | legacy archive | 新 ledger 从 v0 开始 |

## 4. 字段映射

### posts → items

```text
items.id            = posts.id                    # 保持链接稳定
items.app           = "report"
items.type          = "report.note"
items.title         = ""                          # posts 无 title
items.body          = posts.body
items.metadata_json = {
  "legacy_kind": posts.kind,
  "legacy_author": posts.author,
  "thread_id": posts.thread_id,
  "parent_id": posts.parent_id,
  "legacy_meta": posts.meta_json,
  "source": "beta.28"
}
items.created_at    = posts.created_at
items.updated_at    = posts.created_at
```

### attachments → blobs

```text
blobs.id            = attachments.id
blobs.item_id       = attachments.post_id
blobs.filename      = attachments.filename
blobs.content_type  = attachments.content_type
blobs.bytes         = attachments.bytes
blobs.sha256        = attachments.sha256
blobs.created_at    = attachments.created_at
```

从 `home/blobs/<id>` 复制到新 `data/blobs/<id>`；复制后校验 sha256/bytes。

### facts → items

```text
items.id            = facts.id
items.app           = "project"
items.type          = "project.fact"
items.title         = facts.claim
items.body          = facts.evidence
items.metadata_json = {
  "project": facts.project,
  "source": facts.source,
  "status": facts.status,
  "confidence": facts.confidence,
  "created_by": facts.created_by,
  "reviewed_by": facts.reviewed_by,
  "legacy_tags": facts.tags
}
```

### projects → Project DB + Core 投影

Project App 保留全部字段：

```text
id, code, name, description, type, status, machine_id,
review_status, completeness, maturity, commercial_potential,
direction, review_notes, reviewed_at, reviewed_by,
created_at, updated_at
```

Core 投影：

```text
items.id   = "project:" + projects.id
items.app  = "project"
items.type = "project.project"
items.title= projects.name
items.body = projects.description
items.metadata_json = review 字段 + code + machine_id
```

### project_* 表

保留原行与 foreign key：

```text
project_sources
project_entries
project_schemas
project_apps
project_evaluations
```

`project_entries` 最大；每 500 行一个事务批量插入。不要为每个文件建 Core item。

### tasks

Project App DB 保留全部字段。`project.task` Core 投影可选；v0 默认**不投影**，避免搜索噪音。若开启：`items.id = "task:" + tasks.id`。

## 5. Legacy archive

未映射数据导出到：

```text
legacy/
  post_summaries.jsonl
  mentions.jsonl
  reads.jsonl
  presence.jsonl
  tag_aliases.jsonl
  schema_migrations.json
  manifest.json
```

规则：

- JSONL，一行一条，UTF-8
- 不含密钥
- 新工作区备份包含 legacy
- 不进入 Core API
- `post_summaries` 不供 Core v0 使用，仅审计

## 6. 迁移工具行为

```bash
loomsci migrate-v0 \
  --from <beta28-home> \
  --to <new-core-home> \
  --dry-run
```

`--dry-run`：

- 检查源 schema 和计数
- 列出已映射/未映射表
- 估算输出大小
- 不写任何文件

`--apply`：

1. 目标必须为空
2. 创建临时工作区
3. 复制 blobs 并校验
4. 批量插入 items/tags
5. 如选 Report，创建 Report DB
6. 如选 Project，创建 Project DB
7. 导出 legacy archive
8. 写 `migration-report.json`
9. 校验计数与 hash
10. 原子改名到目标
11. 源保持不变

v0 不做原地升级。

## 7. 校验

必须：

- posts 数 = `report.note` items 数
- attachments 数 = blobs 数
- blob sha256/bytes 与源一致
- facts 数 = `project.fact` items 数
- projects 数 = Project DB 行数
- project_entries 数保留
- tasks 数保留
- 迁移后源工作区字节不变
- 不复制 token
- 生成新 `local.token`
- FTS 重建后能搜到已知帖子
- migration report 列出所有计数/hash

## 8. 失败与回滚

- blob hash 不匹配 → 切换前中止
- 计数不匹配 → 切换前中止
- 源 DB 只读打开
- 失败删除临时工作区
- 目标从不覆盖
- 切换失败时源仍是活动工作区

## 9. Windows 与 macOS

- 使用 SQLite read-only URI/backup 保证一致读
- 处理空格、Unicode 路径
- Windows 文件锁：源 DB 绝不写入
- 保留大小写敏感的 ID
- `shutil.copy2` 复制 blobs，复制后校验
- 两个平台都用 beta.28 工作区副本测试

## 10. 验收

1. Dry-run 列出所有表与计数
2. macOS apply 计数正确
3. Windows apply 计数正确
4. 3,586 project entries 保留
5. blob hash 匹配
6. legacy 包含 summaries/mentions/reads
7. Core 表中没有 `post_summaries`
8. 源工作区前后 hash 一致
9. 对另一个目标重跑幂等
10. 失败迁移不留下目标工作区
11. 迁移后搜索可用
12. 新 token 已生成

## 11. 待定

- posts 的 author 放 metadata 还是 App DB
- facts 默认归 Report 还是 Project
- tasks 是否生成 Core 投影
- project_entries 是否需要 DuckDB/parquet 导出
- v0 是否提供 `--replace`
