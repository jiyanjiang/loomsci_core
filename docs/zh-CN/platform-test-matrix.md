# 平台测试矩阵 · Core + Apps

- 状态：M0 草案，2026-11-14
- 必测平台：macOS（A 机）与 Windows（B 机）
- 规则：Core 平台门禁不接受单平台豁免

## 1. 机器

```text
A  macOS arm64    主开发 + Core host
B  Windows x64    第二主个人系统；安装/更新/路径/文件锁测试
```

两台机器使用同一个签名包、同一套契约测试。

## 2. M0 门禁

| 领域 | 测试 | macOS | Windows |
|---|---|---|---|
| Process | install → start → health → stop → update → remove | 必测 | 必测 |
| Process | App 崩溃/重启策略 | 必测 | 必测 |
| Process | 30s health 超时 | 必测 | 必测 |
| Runtime | uv 管理 Python，无需手动安装 | 必测 | 必测 |
| Runtime | 每 App 独立 venv | 必测 | 必测 |
| Data | item + blob + App DB 恢复 | 必测 | 必测 |
| Data | App 更新保留数据 | 必测 | 必测 |
| Data | App 卸载保留数据 | 必测 | 必测 |
| Signing | `signing-trust.md` S1–S12 | 必测 | 必测 |
| Installer | 干净安装，不创建重复工作区 | 必测 | 必测 |
| Installer | 验证失败不留半安装 | 必测 | 必测 |
| Paths | 空格、Unicode、长路径、跨盘 | 必测 | 必测 |
| File lock | 替换/更新前先停止 | 必测 | 必测 |

## 3. 当前状态

```text
process contract prototype   macOS PASS   Windows PASS
signing prototype S1–S12     PASS*       PASS*
backup/restore prototype     PASS        PASS
uv bootstrap                 PASS        PASS
Linux                        M0 不要求；后续

`*` S10 只是前置检查，不是完整安装器。`**` 测试机已有 uv；无 uv 的干净机器下载 uv 尚未验证。
```

## 4. 测试规则

- 每个破坏性测试使用干净/临时工作区
- 记录 OS 版本、arch、包 sha256、测试时间
- Windows 通过不能替代 macOS 通过，反之亦然
- 一个 OS 无法运行 = `blocked`，不是 `pass`
- 所有必测行在两个平台都通过，才能退出 M0

## 5. 证据

每次运行产出：

```text
reports/core_m0/<date>-<os>-<test>.json
```

格式：

```json
{
  "os": "...",
  "arch": "...",
  "package_sha256": "...",
  "test": "...",
  "result": "pass|fail|blocked",
  "started_at": "...",
  "elapsed_ms": 0,
  "error": null
}
```
