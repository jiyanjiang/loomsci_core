# LoomSci Core 0.2.0-rc.3 帮助

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
左侧：内容 / 标签 / 回收站 / 站点 / 工具 / 设置 / CN-EN
中间：发布器、搜索、标签云、item 列表、item 详情
右侧：可选详情栏；item 在主区域打开时隐藏
```

## 内容

- 直接写 Markdown，没有标题字段。
- 支持标题、粗体、代码、表格、链接。
- 支持 `$...$` 与 `$$...$$` LaTeX。
- 可粘贴图片或选择文件，发布前显示缩略图。
- 附件使用文件卡片，显示类型图标、MIME、大小、打开和下载。
- PDF 内嵌预览；Markdown 附件在详情中嵌套渲染。
- 点击 item 在主区域打开详情；右侧详情栏隐藏，工作区变为单列。
- 点击图片缩略图打开画廊；上一张/下一张循环，Esc 关闭。
- 删除会移入回收站；可恢复；永久删除会清理磁盘上的 Blob。

## 搜索与标签

- 搜索正文和标题；回收站中的 item 不参与搜索。
- 标签云显示 Top 20 标签及数量；「全部标签」进入可搜索的标签页。
- item 卡片最多显示 3 个标签和 `+N`；完整标签在详情和标签页。
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

## 备份与恢复

### 备份包含什么

```text
data/core.db
data/blobs/
apps/<slug>/data/
```

不包含：

```text
local.token
Core 代码
venv
日志
```

### 创建备份

1. 打开左侧「设置」
2. 找到「数据备份」
3. 点「创建备份」
4. 列表中出现 `backup-YYYYMMDDTHHMMSSZ`

备份目录：

```text
core-home/backups/
```

### 验证备份

在备份列表中点「验证」。
成功显示「备份验证通过」；失败说明 manifest 或文件哈希不一致。

### 恢复备份

恢复只能写入一个**不存在的新目录**，不会覆盖当前运行工作区。

示例：

```bash
# 恢复后启动新工作区
python -m loomsci_core --home /tmp/loomsci-restored --port 8796 start
```

在设置页：

1. 在「恢复到空目录」填入 `/tmp/loomsci-restored`
2. 在备份列表中点「恢复」
3. 启动恢复后的工作区：

```bash
python -m loomsci_core --home /tmp/loomsci-restored --port 8796 start
```

4. 打开 `http://127.0.0.1:8796/`

Windows 示例：

```powershell
.\.venv\Scripts\python -m loomsci_core --home C:\Users\you\loomsci-restored --port 8796 start
```

恢复后的工作区会生成新的 `local.token`。
不要直接恢复覆盖正在运行的 `core-home`。


```text
core-home/data/core.db
core-home/data/blobs/
core-home/apps/<slug>/data/
core-home/backups/
core-home/local.token
```

schema 版本为 `PRAGMA user_version = 2`。旧库升级前会先复制为
`core.db.pre-v2-*`；未来版本会拒绝启动。

## 更新

## 工具目录

## App 地址与单端口访问

App 仍然在独立进程中运行，但浏览器只使用 Core 的来源：

```text
http://127.0.0.1:8795/apps/<slug>/
```

Core 把 `/apps/<slug>/` 代理到 App 的内部 loopback 端口。内部端口只是实现细节，
不在 UI 中暴露。


打开 `#/tools`，输入 catalog JSON 地址或本地路径，点「检测」。

```json
{
  "format": "loomsci-catalog/1",
  "apps": [
    {
      "slug": "report",
      "name": "LoomSci Report",
      "version": "0.1.0",
      "repo": "https://github.com/example/loomsci-report",
      "description": "Research report generator"
    }
  ]
}
```

开发时可用本地 `source` 路径；正式 `repo` 必须是 `https://github.com/` 地址。
安装使用现有 App Host，不会自动运行 App。


```bash
python -m loomsci_core update check <manifest.json>
python -m loomsci_core update apply <manifest.json> --package <payload.zip>
```

manifest 必须使用 HTTPS（测试可用本地文件），使用 Ed25519 签名，包含
`product`、`version`、`min_core`、`sha256`、`signature`。apply 会备份数据、保存代码快照、
停止 Core、替换包、启动 Core，失败时回滚。公钥位于
`loomsci_core/update_public_key.pem`。

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

- Core 自更新已实现 CLI，但尚未在设置页提供入口。
- 尚无从 GitHub 安装 App。
- 尚无 Report App。
- 尚未做压力测试。
- Windows 已完成测试、截图和鼠标点击，但尚未由独立外部用户按文档走查。
