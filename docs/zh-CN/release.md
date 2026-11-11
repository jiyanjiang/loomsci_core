# 发布与升级

## 构建安装包

```bash
python scripts/build_release.py --out dist
```

输出：

```text
dist/loomsci_core-<version>.zip
dist/loomsci_core-<version>.zip.sha256
dist/latest.json
```

zip 内含 `BUILD_INFO.json` 与 `upgrade-manifest.json`；manifest 说明哪些代码目录可替换、哪些用户数据必须保留。

可选签名：

```bash
python scripts/build_release.py --out releases
```

## 安装

macOS / Linux：

```bash
bash install.sh --package loomsci_core-<version>.zip
```

Windows PowerShell：

```powershell
.\install.ps1 -Package .\loomsci_core-<version>.zip
```

安装器把代码放在 `<home>/core`，数据放在 `<home>/data`、`agents/`、`packs/`、
`logs/`、`runtime/`；旧代码保留为 `<home>/core.prev`。

## 升级 / 回滚

```bash
python scripts/upgrade.py --package loomsci_core-<version>.zip --home <home>
python scripts/upgrade.py --home <home> --rollback
```

升级先在 `<home>/backups/` 创建资产备份；备份失败则中止。随后只替换
`core/`，不改数据目录与 `config.yaml`；交换失败自动恢复旧代码。
`--no-backup` 仅用于诊断。
