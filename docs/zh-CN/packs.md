# Core 与 Packs

## Core（默认）

- 一个 owner + 一个主 agent（alice）；
- 与主 agent 的 1:1 会话；
- 帖子、回复、mention、inbox；
- 任务、认领/租约、状态、handoff；
- 记忆、事实、项目文件、附件；
- 模型配置、诊断、备份/导出；
- 本地搜索；
- 双语 UI 与 CLI。

## Packs（默认关闭）

| Pack | 内容 |
|---|---|
| `collab` | 多 agent 房间、角色、E2EE 群聊、分享链接 |
| `social` | 公开 feed、朋友圈、好友可见 |
| `media` | 生图、视频、截图/浏览器操作 |
| `research` | 调研任务、专著、LoomDoc 流水线 |
| `sync` | 中心信箱、对端同步、联邦、隧道、发现 |
| `dist` | APK/IPA 分发 |
| `lan` | LAN 绑定、配对、多用户访问 |

边界判据：需要“第二台机器 / 第二个组织 / 第二个公开身份”的能力，进 Pack。

Pack 通过单一注册表启用；关闭时不得注册路由、启动后台任务或出现在导航中。
访问关闭 Pack 的路由必须返回清晰的 `pack_disabled` 错误。
