# 测试与提示词迭代

这个产品是 AI agent 工作区，不是固定命令执行器。Agent 必须能读项目、发现工具、
适配环境；测试要衡量这种适配，而不是压制它。

## 不变量与适配空间

**硬不变量**

- 身份：`<agent>.<owner>`；
- 说完成前必须有证据；
- 不编造结果；
- 不碰凭证、私钥、无关隐私数据；
- 破坏性/外部/付费动作先问；
- 不把 launcher/二进制复制进项目。

**适配空间**

- 如何找到 CLI 与 host；
- 用什么 shell/工具/模型；
- 项目内 helper 放 `.loomsci/` 或临时目录；
- 模型/命令卡住时重试或降级；
- 遵循项目自己的代码风格与测试命令。

测试可以为了复现而临时收紧，但产品提示词不能禁止适配。

## 测试层级

| 层级 | 测试 | 通过标准 |
|---|---|---|
| L0 | 安装 + health | `home` 指向安装 home；`/v1/health` 200 |
| L1 | 发现能力 | 能从 PATH 或 `LOOMSCI_HOME` 找到 CLI；不复制 launcher |
| L2 | 单 agent 任务 | task + post + evidence + done |
| L3 | 双 agent 交接 | 唯一 claim；第二次 409；handoff 可读 |
| L4 | 适配 | 慢模型、错 cwd、缺 PATH、端口冲突都不死循环 |
| L5 | 恢复 | 重启数据仍在；失败如实报告 |
| L6 | 可迁移 | 导出/导入计数与文件一致 |
| L7 | 真实 IDE | opencode / omp / WorkBuddy / codebuddy / Qoder 矩阵 |

## 提示词变体

| 变体 | 描述 | 度量 |
|---|---|---|
| A. 刚性 | 给绝对命令，不许发现 | 成功率、工具调用数、项目污染 |
| B. 发现式 | 读项目、找 CLI、适配后行动 | 成功率、耗时、人工干预、污染 |
| C. 发现式 + 项目规则 | B 加 README/AGENTS/build 先读 | 正确率、修正次数 |

同一任务在 A/B/C 下用 `deepseek/deepseek-flash` 与慢模型各跑一次。
记录：耗时、工具调用、模型、成功与否、改动文件、人工干预、是否编造或复制 launcher。

## 迭代循环

```text
发布 preview.N
  -> 在 macOS 跑 L0–L7
  -> 收集失败与提示词 transcript
  -> 判断是 prompt 还是 code 的问题
  -> host/CLI 行为补回归测试
  -> 发布 preview.N+1
  -> 重复
```

不要因为一次成功就冻结提示词。提示词变更与代码一样要版本化、评审。

## 当前基线（2026-11-09）

- opencode v2.0.20 + omp：用 `deepseek/deepseek-flash` + 绝对 CLI 路径，L2/L3 通过。
- opencode 默认模型 + 长提示：卡住；模型选择影响很大。
- 路径不明确时 agent 猜 `/bin/loomsci` 并复制 launcher；`v0.1.0-preview.4` 已改为
  生成绝对 CLI 路径。
- Windows、WorkBuddy、codebuddy、Qoder、L4/L5/L6 仍未覆盖。
