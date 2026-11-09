from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_release  # noqa: E402


@unittest.skipUnless(os.name == "posix" and sys.platform != "win32", "POSIX installer")
class InstallerTest(unittest.TestCase):
    def test_install_and_reinstall_preserves_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = Path(build_release.build(root / "dist")["archive"])
            home = root / "home"
            (home / "data").mkdir(parents=True)
            (home / "data" / "keep.txt").write_text("keep", encoding="utf-8")

            first = subprocess.run(
                [
                    "bash",
                    str(ROOT / "install.sh"),
                    "--package",
                    str(archive),
                    "--home",
                    str(home),
                    "--no-deps",
                ],
                text=True,
                capture_output=True,
                timeout=120,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((home / "core" / "pyproject.toml").is_file())
            launcher = home / "bin" / "loomsci"
            self.assertTrue(launcher.is_file())

            features = subprocess.run(
                [str(launcher), "features", "--json"],
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(features.returncode, 0, features.stderr)
            self.assertLessEqual(json.loads(features.stdout)["route_count"], 80)

            second = subprocess.run(
                [
                    "bash",
                    str(ROOT / "install.sh"),
                    "--package",
                    str(archive),
                    "--home",
                    str(home),
                    "--no-deps",
                ],
                text=True,
                capture_output=True,
                timeout=120,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                (home / "data" / "keep.txt").read_text(encoding="utf-8"), "keep"
            )
            self.assertTrue((home / "core.prev").is_dir())


if __name__ == "__main__":
    unittest.main()
