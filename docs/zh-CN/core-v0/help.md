# LoomSci Core 0.2.0-rc.1 帮助

## 启动

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-core.txt
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 start
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-core.txt
.\.venv\Scripts\python -m loomsci_core --home .\core-home --port 8795 start
```

打开 `http://127.0.0.1:8795/`。

Web UI 使用 HttpOnly SameSite=Strict cookie。CLI 与 SDK 使用
`core-home/local.token` 的 Bearer token。

## 布局

```text
左侧：内容 / 站点 / 设置 / CN-EN
中间：发布器、搜索、标签云、item 列表
右侧：当前 item 详情
```

## 内容

- 直接写 Markdown，没有标题字段。
- 支持标题、粗体、代码、表格、链接。
- 支持 `$...$` 与 `$$...$$` LaTeX。
- 可粘贴图片或选择文件，发布前显示缩略图。
- 附件显示 SHA-256 短名。
- 点击 item 在右侧打开详情。
- Markdown 附件在详情中嵌套渲染。
- 点击图片缩略图打开画廊；上一张/下一张循环，Esc 关闭。

## 搜索与标签

- 搜索正文。
- 标签云显示 Top 1000 标签及数量。
- 点击标签过滤，再次点击取消。
- 列表每次加载 20 个 item。

## 设置

- 用户名。
- DeepSeek API Key，只在本机保存，不写入 Core 日志。
- 本机软指纹，自动生成，30 天轮换。
- 数据备份：创建、列表、验证、恢复到新空目录。

恢复不会覆盖当前运行目录；恢复后的工作区会重新生成 token。

## 站点

- 站点名显示在左侧品牌和页面标题。
- Logo 地址可选；留空则不显示。
- 支持 `http://`、`https://` 或以 `/` 开头的路径。

## 数据

```text
core-home/data/core.db
core-home/data/blobs/
core-home/apps/<slug>/data/
core-home/backups/
core-home/local.token
```

schema 版本为 `PRAGMA user_version = 1`。旧库升级前会先复制备份；未来版本会拒绝启动。

## API / SDK

- CLI / SDK：`Authorization: Bearer <local.token>`。
- Web UI：`GET /` 设置 HttpOnly cookie。
- API 文档：[core-api](core-api.md)，[OpenAPI](../../openapi/core-v0.json)。

## 故障排查

- 端口被占用：换一个 `--port`。
- UI 不连接：检查 `status`，再访问 `/v1/health`。
- 恢复被拒绝：目标目录必须不存在。
- 未来 schema 错误：使用更新的 Core，不要降级数据。

## 当前限制

- 尚无自动更新。
- 尚无从 GitHub 安装 App。
- 尚无 Report App。
- 尚未做压力测试。
- Windows 已完成测试、截图和鼠标点击，但尚未由独立外部用户按文档走查。
