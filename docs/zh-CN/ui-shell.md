# ui-shell 功能目标

`ui-shell` 是第一个 add-on，也是 Core 唯一支持的 UI shell。独立进程 8790，
只消费 Core `/v1`，不 import Core。本阶段明确不做主题/视觉。

## 必须功能

1. **安全 Markdown**
   - 标题、段落、粗斜体、行内代码、代码块
   - 有序/无序列表、引用、分隔线
   - 链接（仅 http/https）、表格
   - 不执行原始 HTML

2. **LaTeX**
   - 行内 `$...$`、块级 `$$...$$`
   - KaTeX 本地内置（不依赖 CDN）
   - 非法表达式显示源码，不崩页面

3. **附件**
   - 图片内联显示
   - 浏览器支持的音频/视频带 controls
   - 其他文件下载
   - 上传本地文件并附加到帖子
   - 从剪贴板粘贴图片到正文编辑器

4. **搜索**
   - 通过 `/v1/search` 搜索 posts/tasks/facts

5. **Core 操作**
   - 发帖
   - 建任务、claim、带 evidence done
   - memory add/review
   - inbox 列表、单条/全部已读

6. **状态**
   - loading / empty / error
   - 不静默失败
   - 键盘可操作

## 非目标

- 主题、动画、富文本编辑器
- PDF/Office 预览
- 转码、缩略图、OCR/转写
- 登录、多用户、中心、sync
- 改 Core 表或 `/v1` 形状

## 验收

macOS 与 Windows 自动浏览器检查必须通过：

- Markdown 表格/代码块
- `$E=mc^2$` 经 KaTeX 渲染
- 图片附件显示 `<img>`
- 音频/视频附件有 `<audio>`/`<video controls>`
- 搜索有结果
- 上传附件并关联帖子
- task claim/done、memory review
- 无原始 HTML 注入

通过后才允许进入下一个 add-on `media`。

## 自检（2026-11-10）

- macOS：Markdown 表格/代码、KaTeX、图片/音频/视频元素、搜索、上传、
  任务/记忆操作、XSS 拒绝 — 通过。
- Windows：Markdown 表格、KaTeX、搜索、发帖 — 通过；使用同一包，媒体元素在
  macOS 验证。

## Baseline theme 门槛

本阶段只做 token + 可访问性，不做品牌或多主题切换。

- 单一 token 源：颜色、间距、字体、圆角
- 通过 `prefers-color-scheme` 跟随系统明暗
- 正文对比度 15.7:1（亮）/ 16.6:1（暗）；muted 5.9:1 / 8.3:1
- 键盘焦点：2px accent outline
- 控件最小高度 36px
- 360px 视口无横向滚动
- 无外部字体/CDN；KaTeX 保持本地

2026-11-10 用真实 Chromium 标签页自检。完整视觉主题、站点名/Logo、i18n、
开版仍分开且后续再做。
