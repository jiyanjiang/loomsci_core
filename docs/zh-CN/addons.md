# Add-on 规划

Core 是长期稳定的内核；UI 和能力都是 add-on。本文是契约规划，不是实现承诺。
按顺序逐个实现；每个 add-on 先证明 Core 契约足够，再开始下一个。

## 原则

1. Core 永不 import add-on 代码。
2. add-on 只走 `/v1` 或公开 Core API，不 import `core.storage` 内部实现。
3. 每个 add-on 有独立路由命名空间、存储命名空间、迁移、版本、测试、卸载路径。
4. 只做加法：不改 Core 表结构，不破坏 `/v1` 形状。
5. UI 是壳：渲染数据、调用 API，不拥有业务真相。
6. 缺某个 add-on 不能让 Core 不可用。
7. 先有两个真实 add-on，再抽象 pack 框架。

## 目录与顺序

| # | Add-on | 用途 | 依赖 | 风险 |
|---|---|---|---|---|
| 0 | `ui-shell` | Markdown、主题、导航、空/错状态 | Core API | 低 |
| 1 | `app-host` | 安装/卸载、`/apps/<slug>/`、manifest/权限、profile | Core pack registry | 中 |
| 2 | `collab` | 房间、线程、角色、presence、增强 handoff | Core posts/tasks | 中 |
| 3 | `notify` | digest、未读摘要、桌面/WezTerm/email 适配 | Core inbox，collab 可选 | 低 |
| 4 | `media` | 图片/音频/视频库、缩略图、OCR/转写 | Core attachments、app-host | 中 |
| 5 | `research` | 来源、引用、笔记、专著/报告工作流 | Core memory、media | 高 |
| 6 | `sync` | 多机身份、备份恢复、中心/对端同步 | Core export/import、app-host | 高 |
| 7 | `social` | 公开主页、feed、好友/邀请、分享链接 | collab + sync | 高 |

`app-host` 可以在第一个 add-on 真正需要独立安装时，再把最小安装/卸载注册表
从 Core 中抽出来；不要提前造框架。

## 默认 profile

| Profile | Add-ons | 场景 |
|---|---|---|
| `minimal` | 无 | 纯 Core，CLI 优先 |
| `personal` | `ui-shell`, `notify` | 单人单机 |
| `maker` | `ui-shell`, `media`, `research` | 创作者/研究者 |
| `team` | `ui-shell`, `collab`, `notify`, `sync` | 小团队 |
| `full` | 全部稳定 add-on | 高级用户，显式选择 |

安装方式：

```bash
loomsci addon list
loomsci addon install ui-shell
loomsci addon install --profile personal
loomsci addon remove ui-shell
```

profile 是推荐组合，不是强制捆绑。

## Manifest

```json
{
  "name": "ui-shell",
  "version": "0.1.0",
  "api": "core/1",
  "requires": ["core/1"],
  "routes": ["/apps/ui/*"],
  "storage": "addon.ui",
  "migrations": ["001_init.sql"],
  "jobs": [],
  "nav": [{"label": "UI", "href": "/apps/ui/"}],
  "preserve": ["data/addons/ui/"]
}
```

规则：

- `api` 是 Core 契约版本，不是 add-on 自身版本。
- `routes` 必须在 `/apps/<name>/` 下，除少量批准的 Core UI 槽位。
- `storage` 映射到隔离目录和/或表前缀。
- `migrations` 只做加法且幂等；不跨 add-on 建表。
- `jobs` 只有 profile 启用该 add-on 时才运行。
- `preserve` 按策略在升级/卸载时保留。

## 实现顺序

### Phase 0：N4 冻结

完成 `docs/zh-CN/n4-acceptance.md` 的场景矩阵，冻结 Core contract v1。
在此之前不写 add-on 代码。

### Phase 1：`ui-shell`

- Markdown、代码块、安全链接
- 改善 posts/tasks/memory/inbox/attachments 视图
- 不改 Core API，不建新表
- 验证 shell 边界

### Phase 2：`app-host`（仅在需要时）

- 安装/列出/卸载 add-on
- profile 选择
- manifest 校验与版本兼容
- 暂不做市场/联网

### Phase 3：`collab`，然后 `notify`

- 基于 Core posts/tasks 的房间/线程
- 基于 Core inbox/mentions 的通知
- 暂不做 E2EE、中心、远程同步

### Phase 4：`media`，然后 `research`

- media 依赖 attachments
- research 依赖 memory + sources + media
- 各自独立存储和迁移

### Phase 5：`sync`，然后 `social`

- sync 风险最高：身份、冲突、备份、升级兼容、真实双节点测试
- social 在 sync/collab 稳定后
- E2EE 如要做，是 sync/collab 扩展，永不进入 Core

## 不要做

- 不要把中心、登录、TLS、多用户加进 Core。
- 不要让 UI import Core 内部模块。
- 不要把版本数据写进壳。
- 不要所有 add-on 共用一个 schema。
- 不要在两个真实 add-on 之前做插件市场。
- 不要让 `sync` 进入 Core 关键路径。

## 单人维护规则

- 一次只做一个 phase；测试和文档完成后再下一个。
- 每个概念只有一个真相源。
- 每个 add-on 可卸载而不丢 Core 数据。
- 每次升级都有回滚和旧 export 导入测试。
- 包、文档、checksum 一致才发布。
- 宁可删除功能，也不维护两套实现。
