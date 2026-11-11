from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import doctor, storage  # noqa: E402
from core.home import ensure_layout  # noqa: E402


class DoctorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_missing_database_is_not_ok(self) -> None:
        result = doctor.run(self.home, port=1)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["database"]["ok"])

    def test_initialized_home_is_ok(self) -> None:
        layout = ensure_layout(self.home)
        storage.init_db(layout.db)
        result = doctor.run(self.home, port=1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["checks"]["database"]["integrity"], "ok")
        self.assertFalse(result["checks"]["core"]["ok"])
        self.assertTrue(any("core is not reachable" in item for item in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
