# 备份资产边界

`loomsci backup inspect` 是只读清单，不创建、删除或改写文件。

## 分类

| 类别 | 默认 | 例子 |
|---|---|---|
| 资产 | 包含 | SQLite 数据、agent 人格、笔记/帖子、生成媒体、程序/资产、add-on 数据 |
| 参考资料 | 仅元数据 | 下载的 PDF 论文、电子书、数据集、压缩包 |
| 派生 | 排除 | 缩略图、缓存、预览文件 |
| 排除 | 排除 | 代码包、虚拟环境、日志、runtime、临时文件 |
| 秘密 | 永不包含 | key、token、密码、`.env`、含凭据的配置 |

参考资料二进制不进入资产备份；未来 bundle 可用 `references.json` 保留元数据。

## 命令

```bash
loomsci backup inspect
loomsci backup inspect --json
loomsci backup create --out assets.zip
loomsci backup show assets.zip
loomsci backup restore assets.zip --to <empty-home>
loomsci backup restore assets.zip --to <empty-home> --apply
```

发现秘密会阻止未来的导出，或要求显式脱敏；清单不会打印秘密值。

## 不进入备份

- 第三方 PDF/论文（保留引用/索引）
- API key、密码、私钥、token
- 虚拟环境、node_modules、缓存、日志、runtime
