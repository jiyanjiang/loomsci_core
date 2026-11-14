# 数据分层与备份语义 · v0

- 状态：M0 草案，2026-11-14
- 适用：LoomSci Core + Apps
- 关联：`core-contract.md`、`app-manifest.md`
- 决策：Core `items` 是可读 artifact 的真相源；App 数据库是领域状态与关系的真相源。

## 1. 分层模型

```text
Core
├─ core.db        可读 artifact 内容、tags、app 注册表
├─ blobs/         附件/图片/PDF
└─ FTS            派生搜索索引

App
├─ apps/<slug>/data/app.db   领域状态/关系
└─ 引用 Core item id
```

App 不得写另一个 App 的数据库。跨 App 可读内容必须走 Core `items`。

## 2. 数据归属

| 数据 | 真相源 | 例子 |
|---|---|---|
| 报告正文、标题、摘要 | Core `items` | Report Markdown |
| 标签 | Core `item_tags` | `physics` / `pisa` |
| 图片/PDF/附件 | Core `blobs` | 图表、来源 PDF |
| 搜索索引 | Core 派生 | FTS5 |
| 来源登记 | Report App DB | DOI/URL/excerpt |
| 阅读进度/高亮 | Report App DB | 本地状态 |
| 项目/任务/决策关系 | Project App DB | task 属于 project |
| Agent 角色/Handoff | Project App DB | 本地项目状态 |
| 渲染任务/模板 | Report App DB | PDF/EPUB pipeline |

规则：

```text
可读 artifact → Core item
工作流/关系/状态 → App DB
```

App 可以为可搜索实体创建 Core item 投影，但不得复制正文；App DB 存 item id。

## 3. Item 类型约定

```text
<app>.<type>
```

例子：

```text
report.report
report.source_note
project.project
project.decision
monograph.chapter
```

`metadata_json` 由 App 定义；v0 不做全局 schema，App 在 manifest 声明 `metadata_schema_version`。

## 4. Report 映射

```text
Core Report item
  type: report.report
  title: 报告标题
  body: 规范 Markdown
  metadata_json: { "style_code": "...", "audience": "...", "status": "..." }
  tags: [...]
  blobs: 图表、PDF、来源快照

Report DB
  sources: DOI/URL/title/license/excerpt/hash
  evidence: claim -> source -> level
  render_jobs: md/pdf/epub 路径/状态
  reading_state: 已读/高亮/笔记
```

删除 Report item 时，App 必须同步删除 Report DB 行，或标记 orphan。

## 5. Project 映射

```text
Core Project item
  type: project.project
  title: 项目名
  body: 简短概述
  metadata_json: { "status": "...", "review_status": "..." }

Project DB
  projects: 项目记录与配置
  tasks: 引用 project item 的任务
  decisions: 决策记录
  evidence_links: item/source 关系
  agent_roles: 角色与 handoff
```

v0 不要求 task/decision 成为 Core item；若需要跨 App 搜索，App 创建 `project.task` 投影。

## 6. 跨 App 访问

v0 删除 `items.cross_read`。

- App 只能读自己的 namespace
- 跨 App 共享走未来的显式导出/导入 API
- v0 不做 App-to-App RPC
- Core 最小 UI 可以读投影，但不暴露 App 原始 DB

## 7. 备份范围

默认备份 **数据型完整工作区**：

```text
manifest.json
data/core.db
data/blobs/
apps/<slug>/data/
apps/installed.json
```

默认排除：

```text
local.token
logs/
runtime/
venvs/
app code
caches
临时文件
```

可选 `--with-code` 增加 App 代码，用于离线恢复。Core 代码不在数据备份内；从签名包重装。

## 8. 备份格式

```text
backup-<timestamp>/
├─ manifest.json
├─ data/
│  ├─ core.db
│  └─ blobs/
└─ apps/
   ├─ installed.json
   └─ <slug>/data/
```

`manifest.json`：

```json
{
  "format": "loomsci-backup/1",
  "created_at": "...",
  "core_version": "...",
  "core_api": "core/1",
  "apps": [{"slug": "report", "version": "...", "data_namespace": "app_report"}],
  "files": [{"path": "data/core.db", "sha256": "...", "bytes": 0}]
}
```

规则：

- SQLite 用一致快照（`VACUUM INTO` 或 checkpoint+copy）
- 先写临时目录，校验后原子改名
- 不覆盖已有备份
- manifest 不包含密钥/token

## 9. 恢复模式

v0 只支持：

```text
--new       恢复到空工作区（默认）
--replace   仅在显式 --force 下替换现有工作区
```

v0 不做部分合并。

恢复流程：

1. 校验 manifest 和每个文件 hash
2. 解压到临时工作区
3. 验证 Core DB 可打开、App manifest 可解析
4. 全部通过后再切换
5. 失败时保持现有工作区不变
6. 重新生成 `local.token`
7. App 版本不兼容时不自动启动

## 10. App 版本不匹配

- 版本不同也恢复数据；App 标记 `needs_install` / `needs_update`
- Core 不带该 App 启动
- 用户安装兼容版本前，App 数据保持不变
- v0 不自动迁移 App 数据

## 11. 卸载

- App 卸载删除代码，默认保留 `apps/<slug>/data/`
- `remove_data` 必须显式确认
- Core 卸载保留 `data/` 与 `apps/*/data/`；`--purge` 需显式确认

## 12. 验收

1. Core DB + blob + App DB 能恢复到干净工作区
2. 恢复保留 item id、tags、blobs、App 关系
3. `local.token` 不恢复，重新生成
4. 截断备份在切换前被拒绝
5. App 版本不匹配不删除数据
6. App 卸载保留数据
7. 备份默认排除 venv、日志、代码
8. manifest 列出每个文件 sha256 与 bytes
9. 非空工作区恢复必须 `--force`
10. 恢复失败保持现有工作区不变
