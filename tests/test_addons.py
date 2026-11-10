from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import addons  # noqa: E402


class AddonHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_available_install_remove_profile(self) -> None:
        names = [item["name"] for item in addons.available()]
        self.assertIn("ui-shell", names)
        result = addons.install(self.home, "ui-shell")
        self.assertTrue((self.home / "packs" / "ui-shell" / "manifest.json").is_file())
        self.assertIn("ui-shell", addons.installed(self.home))
        self.assertEqual(result["name"], "ui-shell")
        data = self.home / "packs" / "ui-shell" / "data"
        data.mkdir()
        (data / "state.json").write_text("{}")
        addons.install(self.home, "ui-shell")
        self.assertTrue((data / "state.json").is_file())
        addons.remove(self.home, "ui-shell")
        self.assertTrue((data / "state.json").is_file())
        self.assertNotIn("ui-shell", addons.installed(self.home))
        installed = addons.install_profile(self.home, "personal")
        self.assertEqual([item["name"] for item in installed], ["ui-shell"])
        with self.assertRaises(addons.AddonError):
            addons.install(self.home, "missing")


if __name__ == "__main__":
    unittest.main()
