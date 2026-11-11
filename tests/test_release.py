from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_release  # noqa: E402
import upgrade  # noqa: E402


class ReleaseTest(unittest.TestCase):
    def test_build_and_upgrade_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "dist"
            result = build_release.build(out)
            archive = Path(result["archive"])
            self.assertTrue(archive.is_file())
            self.assertTrue((out / "latest.json").is_file())
            self.assertTrue((out / f"{archive.name}.sha256").is_file())

            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
                self.assertTrue(any(name.endswith("/upgrade-manifest.json") for name in names))
                self.assertTrue(any(name.endswith("/BUILD_INFO.json") for name in names))
                self.assertTrue(any(name.endswith("/core/app.py") for name in names))
                self.assertFalse(any(name.endswith(".key") for name in names))

            home = root / "home"
            (home / "core").mkdir(parents=True)
            (home / "core" / "old.txt").write_text("old", encoding="utf-8")
            (home / "data").mkdir()
            (home / "data" / "data.db").write_bytes(b"keep")
            upgraded = upgrade.apply(archive, home, backup=False)
            self.assertTrue(upgraded["ok"])
            self.assertTrue((home / "core" / "pyproject.toml").is_file())
            self.assertFalse((home / "core" / "old.txt").exists())
            self.assertEqual((home / "data" / "data.db").read_bytes(), b"keep")
            self.assertTrue((home / "core.prev").is_dir())

            rollback = upgrade.rollback(home)
            self.assertTrue(rollback["ok"])
            self.assertTrue((home / "core" / "old.txt").is_file())
            self.assertEqual((home / "data" / "data.db").read_bytes(), b"keep")

    def test_latest_matches_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            result = build_release.build(out)
            latest = json.loads((out / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["sha256"], result["sha256"])
            self.assertEqual(latest["product"], "loomsci_core")
            manifest = json.loads((out / "release-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["file"], Path(result["archive"]).name)
            self.assertEqual(manifest["sha256"], result["sha256"])
            self.assertEqual(manifest["channel"], "beta")


if __name__ == "__main__":
    unittest.main()
