# 源码复用映射 · S1

> 状态：S1–S3 已开始。已有 `core/home.py`、`core/profile.py`、`core/packs.py`、
> `core/local_auth.py`、`core/storage.py`、`core/handoff.py`、`core/alice.py`、
> `core/export.py`、`core/app.py`、`presets/agents/alice/` 与
> `home`/`migrate`/`features`/`serve`/`post`/`read`/`presence`/`handoff`/
> `alice`/`export`/`import` CLI；尚未复制旧模块。
> 目标：从现有 TAA 代码中抽出最小可用 Core 到公共仓库，运行时**不依赖**旧仓库。

## 规则

1. **单向复制**：不软链、不从私有 checkout import、不依赖旧仓库运行。
2. **v1 保留 `core/` 包名**：对外 CLI 叫 `loomsci`；全仓改包名会带来大面积 import 迁移风险。
3. **只用 allowlist**：只复制选定文件；去掉数据、密钥、本地路径、私有文档。每次 push 前跑脱敏自检。
4. **Core 不包含 Pack 代码**：中心、对端、联邦、分发、调研、媒体、执行器循环都不进 Core。
5. **每个复制模块都要有测试**，且在 macOS 与 Windows 都跑。

## 复用矩阵

| TAA 资产 | 决定 | 说明 |
|---|---|---|
| `core/agent_identity.py` | 复制 | `agent.owner` 句柄规则；补测试 |
| `core/db.py` + schema | 改造 | 裁剪表；路径从 `home.py` 来；只做加法迁移 |
| `core/persona.py` | 改造 | alice 基线；Core 关闭 body/wardrobe |
| `core/memory.py` / memory vault | 改造 | 每 agent 私有记忆；不假设 Pack |
| `core/attachments.py` | 改造 | 内容寻址附件；大小/类型限制 |
| `core/redaction.py` | 复制 | 发帖、导出、演化、发布前检查 |
| `core/i18n.py` + `locales/` | 复制 | zh-CN/en 键对齐；只翻功能面 |
| `core/protocol.py` | 复制 | 协议版本与能力清单 |
| `core/distribution.py` | 改造 | 签名清单 + 固定公钥；禁止自签自证 |
| `core/updates.py` | 改造 | 强制 sha/bytes/channel；跨平台；不要 import 即 `fcntl` |
| 备份/导出模块 | 改造 | 只取非 peer 部分；JSON + Markdown + 附件 |
| `static/teamai/` | 子集 | 只留 Core 页面；无 Pack 导航 |

| TAA 资产 | 决定 | 说明 |
|---|---|---|
| `core/server.py` | 改造 | 只暴露小路由 allowlist；不要照搬 317 条 |
| `core/app_ui.py` | 改造 | Core 页面：home、chat、activity、tasks、memory、settings、diagnostics |
| `core/auth.py` | 替换 | 本地身份头 + Host/Origin/JSON 边界 |
| `core/community.py` | 改造 | 帖子、回复、mention、inbox；去掉公开/好友可见 |
| `core/rooms.py` | 子集 | 只保留 1:1 会话；不做多 agent 房间 |
| 任务模块 | 改造 | claim/lease/status/done；同一任务唯一有效租约 |
| `core/commands.py` | 暂缓 | Core 用本地 CLI 即可 |

| TAA 资产 | 决定 | 原因 |
|---|---|---|
| `center_hub.py`、`center_sync.py` | 排除 | 无中心 |
| `federation.py`、`peer_*`、`discovery.py`、`hub*.py`、`tunnel_client.py` | 排除 | 仅 Pack |
| `group_crypto.py`、`attach_crypto.py` | 暂缓 | collab Pack；单机 Core 不需要 |
| `appdist.py`、`video`、`research.py`、`monograph.py`、`loomdoc_ui.py`、`media.py`、`weather.py` | 排除 | Pack 或示例 |
| `executor_bridge.py`、`chatwork.py`、`runtime/dispatcher.py`、`runtime/*_agent.py` | 排除 | IDE 才是执行器 |
| 分享/二维码/邀请/join | 排除 | collab Pack |

## 新增模块

| 模块 | 用途 |
|---|---|
| `core/home.py` | `LOOMSCI_HOME` 解析；旧 home 检测；复制迁移；双 home 冲突拒绝 |
| `core/profile.py` | `core` / `team` profile 选择 |
| `core/packs.py` | 路由、后台任务、导航的单一注册表 |
| `core/local_auth.py` | 本地身份头、Host 白名单、Origin、JSON 校验 |
| `core/presence.py` | 每 agent 的 IDE 会话记录 |
| `core/reads.py` | 每 agent 读游标 |
| `core/handoff.py` | 交接帖校验与渲染 |
| `cli/loomsci.py` | 对外 CLI |
| `presets/agents/alice/` | persona、instructions、adapters |

## 目标目录

```text
core/
  home.py profile.py packs.py local_auth.py
  db.py identity.py persona.py memory.py attachments.py redaction.py
  community.py tasks.py presence.py reads.py handoff.py
  i18n.py protocol.py distribution.py updates.py
cli/
  loomsci.py
presets/agents/alice/
locales/
static/teamai/        # 只留 Core 最小资产
tests/
```

## S1 切片

| 切片 | 交付 | 验收 |
|---|---|---|
| S1.1 | `home.py`：`LOOMSCI_HOME`、旧 home 检测、`migrate --dry-run` | 不双写；迁移计数报告 |
| S1.2 | `profile.py` + `packs.py`；路由/任务/导航闸门 | Core `features` ≤80；关闭 Pack 返回 `pack_disabled`；无 Pack 循环 |
| S1.3 | `local_auth.py` 接入最小 app | 只绑回环；坏 Host/Origin/表单/超大 body 被拒 |
| S1.4 | 最小 health/version/features + 一条帖子/任务路径 | 匿名读不到私有数据 |
| S1.5 | macOS + Windows 测试 | 两平台同测试通过；无 POSIX-only import |

## 非目标

- 复制全部路由或 UI；
- 本阶段迁移真实用户数据；
- 启用任何 Pack；
- 做安装器；
- 多 agent 房间、E2EE、中心、对端、公开 feed。

## 待定

- 逐模块 cherry-pick，还是整包复制后加闸门。建议 cherry-pick，再加闸门；整包复制会让 317 条路由继续存活。
- 最小依赖：先 Flask + PyYAML；cryptography 只在需要处引入。
- 文件锁抽象：POSIX `fcntl` / Windows `msvcrt`，不要 import 时平台崩溃。
