# N4 验收：场景，而不是挂机时长

Core 是单机产品。没有真实负载的双机挂机 soak 不能证明质量：它只证明进程
能活着，不能覆盖租约、冲突、迁移或恢复。

N4 的完成条件是在 macOS 与 Windows 的全新 home 上通过一组**确定性场景**。
耗时只是结果，不是验收标准。

## 为什么不需要双机 soak

- Core 没有 sync、中心、联邦或多用户状态。
- macOS 与 Windows 是两个独立安装，不是两个副本。
- 跨机行为属于未来的 `sync` add-on，应当在该 add-on 出现时用真实双节点测试。
- 长时间空闲无法触发租约、并发冲突、迁移和恢复。

第二台机器的价值是**平台一致性**和真实 IDE 证据，不是空闲 soak。

## 场景矩阵

每项都在隔离 home、限定负载下执行。

### A. 安装与契约

- 安装包、home 解析、启动 host
- `/v1/health`、`/v1/version`、`/v1/status`
- `features`：只暴露实际路由，nav/packs 正确
- 检查安装树内 README/VERSION

### B. Core 生命周期

- owner + 默认 agent
- post / read / cursor
- task add / claim / 第二次 409 / done + evidence
- handoff 可被目标 agent 读回
- memory add / review / search
- mention inbox / 标记已读
- attachment 上传、关联帖子、下载
- SSE `since=0&once=1` 与从后续 cursor 重连

### C. 并发

- N 个任务、两个 agent 竞争：恰好一个 `200`、一个 `409`
- 3 个 agent 并发发帖：序号不丢、不重复
- 写入过程中重复 export：导出仍可解析

### D. 故障与恢复

- 未知 agent → 403
- 非法句柄 → 400
- 缺失/重复附件 → 404/409，不产生孤儿帖
- 端口已占用 → exit 2，不出现第二个 listener
- 损坏 export → 导入失败且不污染目标
- 重启 host：计数与 integrity 不变
- 升级 → 回滚：代码恢复、数据保留

### E. 平台一致性

macOS 与 Windows 都跑 A–D，结果应一致；差异必须记录，不能静默跳过。

真实 IDE L7 是独立证据：

- macOS：opencode + omp
- Windows：opencode + omp（安装后）
- GUI 适配器是人工证据，不作为 Core 阻塞项

### F. 兼容性

- 导入上一 preview 的 export
- 已有 DB 的加法迁移
- 旧的 Windows 无 `.cmd` 指令可被检测并重新生成

## 限定负载

每台机器建议至少：

```text
3 agents × 80 posts       = 240 帖
20 tasks, 2 racing claims = 20 × (200 + 409)
20 facts + 20 reviews
1 attachment upload/link/download
1 SSE first connect + 1 reconnect
1 export/import round-trip
1 restart
1 upgrade/rollback（有上一版包时）
```

这组场景是确定性的，几分钟即可完成；它比一小时空闲更能发现真实问题。

## 出口

满足以下条件即 N4 完成：

1. macOS 与 Windows 都通过 A–F；
2. 失败项已修复，或有明确、被接受的例外；
3. 文档与安装包内 README/VERSION 一致。

N4 开始后不再加功能，只修 bug 和补测试。
