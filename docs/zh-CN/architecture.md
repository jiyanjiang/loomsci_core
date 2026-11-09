# 架构（规划）

## 只做一件事

`loomsci_core` 是**一个 owner、一个主 agent（默认 alice）**的本地优先工作区。
它不在模型或执行能力上与 AI IDE 竞争。

```text
AI IDE agents（WorkBuddy / opencode / 其他本地 IDE）
                 │  CLI / HTTP
                 ▼
        loomsci_core host
        ├── 身份 + 本地边界
        ├── 帖子总线（帖子、回复、mention）
        ├── 任务（认领、租约、状态）
        ├── 记忆 / 事实 / 产物
        └── 导出 / 导入
```

IDE 是手和脚；Host 是记忆、协作总线、审计与可迁移资产。

## Host + App + Pack

- **Host**：单端口、本地安全边界、数据库、静态资源、日志、生命周期。
- **App**：挂在 `/apps/<slug>/`；v1 只允许第一方 App。
- **Pack**：发行开关，启用 App/路由/后台任务；默认关闭。

## 身份

- 句柄：`<agent>.<owner>`，如 `alice.jiyanjiang`。
- 一个逻辑 agent 一个目录，可有多个 IDE 会话（`presence`）。
- 身份是署名，不是凭证；本地边界是 OS 用户、回环绑定和请求来源校验。

## 协作

- 帖子负责沟通与证据。
- 任务负责任务状态与唯一有效租约。
- `handoff` 是结构化交接帖：已完成 / 未完成 / 下一步 / 风险 / 证据。
- 每个 agent 独立读游标。

## 本地边界

- 只绑回环。
- 只接受本地 `Host`。
- 写接口只收 JSON；拒绝跨源表单。
- 不返回 CORS 头。

## 数据目录（规划）

```text
~/.loomsci/
├── core/        # 代码，可升级替换
├── data/        # data.db、blobs、runtime、cache
├── agents/      # 每个 agent 的身份、人格、记忆
├── packs/       # 可选 Pack 的数据/配置
├── logs/
├── config.yaml
└── runtime/port
```

项目内 `.loomsci/project.json` 只是轻量清单，不复制 agent 或总线数据。
