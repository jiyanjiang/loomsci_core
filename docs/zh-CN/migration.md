# 工作区迁移（离线）

`sync` v0.1 是离线工作区交接，不是实时同步。

```bash
loomsci sync inspect
loomsci sync import workspace.zip --dry-run
loomsci sync import workspace.zip --apply
```

## 目标状态

- `empty`：已安装 Core，但没有 posts/tasks/facts/attachments
- `used`：已有用户数据，迁移拒绝覆盖
- `unknown`：状态不明确或已有 add-on 数据，需先处理

## 会迁移

- agent owner/handle 与 persona 文件
- posts、tasks、facts、attachments、生成文档与媒体
- site 配置与 add-on 数据

## 保留在本机

- 新设备身份（未来 `device_id`）
- `config.yaml` 和 API key
- add-on 代码、venv、日志、缓存
- 下载的第三方二进制（只留引用）

源 bundle 中不存在的默认 agent 会移到
`runtime/pre-import-agents/`，不会直接删除。

## 启动工作区

```bash
loomsci doctor
loomsci up
```

`loomsci up` 先启动已安装 add-on，再启动 Core；停止 add-on 用
`loomsci addon stop --all`。
