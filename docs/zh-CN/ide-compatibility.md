# IDE 兼容矩阵与 add-on 契约

LoomSci 不绑定编辑器：Core 提供 loopback HTTP API、CLI 和浏览器 UI，
不需要编辑器插件。编辑器集成只能走 CLI 或公开 `/v1` API，不得 import
Core 内部模块。

## 兼容矩阵

| IDE / 编辑器 | 集成方式 | 状态 | 说明 |
|---|---|---|---|
| 终端（任意 shell） | `loomsci` CLI | 已验证 | A/B beta.20：status、search、projects、addon |
| 浏览器 | `http://127.0.0.1:8790/app/` | 已验证 | 仅 loopback，不监听外网 |
| VS Code | Terminal/Task 调 CLI；Simple Browser 开 UI | 契约兼容 | 未发布扩展 |
| Cursor | Terminal/Task 调 CLI | 契约兼容 | 与 VS Code 同一路径 |
| Windsurf | Terminal/Task 调 CLI | 契约兼容 | 同一路径 |
| JetBrains | External Tool 调 CLI | 契约兼容 | 未发布插件 |
| Zed | Terminal task | 契约兼容 | 仅 CLI |
| Neovim / Vim | `:!loomsci ...` 或 terminal buffer | 契约兼容 | 仅 CLI |
| Emacs | `shell-command` / `vterm` | 契约兼容 | 仅 CLI |
| Xcode | Run Script / 外部终端 | 契约兼容 | 仅 CLI；macOS |

“契约兼容”表示只使用稳定接口，但尚未在该 IDE 内实测。只有真实工作流需要
编辑器原生 UI 时才新增插件。

## 集成规则

- 在项目 home 下调用 `loomsci`，不要直接写 `data.db`。
- 需要机器可读输出时优先用 `--json`。
- 走 `/v1` 时带 `X-Loomsci-Agent`，遵守 `api=core/1`。
- Core 与 add-on 不得绑定非 loopback 地址。
- 不要把 API key 写进编辑器配置或仓库。
- 不要通过 IDE task 执行项目应用代码。

## Add-on manifest 契约

```bash
loomsci addon contract
loomsci addon contract --json
```

必填字段：

```text
name, version, api, package, entry, port, health
```

可选字段：

```text
requires, routes, storage, jobs, nav, preserve
```

规则：

- `api` 必须是 `core/1`。
- `package` 必须是 `packs/` 下可导入的目录名。
- `entry` 必须是该包内的 Python 模块名。
- `port` 是 add-on 的 loopback 端口；`health` 是 HTTP 健康路径。
- `requires` 可用 `>=` 引用 Core 或其他 add-on。
- 安装数据在 `packs/<package>/data/`，`addon update` 保留。
- Core 不 import add-on 代码；add-on 只走公开 `/v1` API。
- 缺少某个 add-on 不得阻止 Core 启动。
