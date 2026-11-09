# 路线图

> 不承诺日期。每个阶段都必须通过 macOS 与 Windows 的验收才算完成。

## G0 · 公共 seed（当前）

- 双语 README 与文档；
- 架构、CLI、Packs、路线图、变更记录；
- 许可证、安全、贡献、行为准则；
- 公共树检查；
- 无可运行 host。

## G1 · Core host

- `~/.loomsci` home 与旧 home 迁移；
- 单回环端口（8787）；
- profile/Pack 闸门；
- 本地身份与请求来源边界；
- 默认只建一个 agent（alice）。

## G2 · 协作总线

- 帖子、回复、mention、inbox；
- 任务、认领/租约、状态、handoff；
- presence 与读游标；
- `loomsci` CLI。

## G3 · 可迁移资产

- 导出/导入与计数校验；
- 项目清单；
- 诊断；
- 首个跨平台安装器。

## G4 · Preview 发布

- macOS 与 Windows 安装器；
- 签名产物与校验和；
- 公共源码快照；
- 社区 issue/discussion 流程。

## 之后

- 可选 Packs（collab/research/media/sync/dist/lan）；
- 可选的公开身份映射；
- `/apps/<slug>/` 工具挂载。
