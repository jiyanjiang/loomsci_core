from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import service  # noqa: E402


class ServiceConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / "bin").mkdir(parents=True)
        for name in ("loomsci", "loomsci.cmd"):
            (self.home / "bin" / name).write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_launchd_payload_uses_detached_up(self) -> None:
        payload = service._plist_payload(self.home)
        self.assertEqual(payload["Label"], service.LABEL)
        self.assertTrue(payload["RunAtLoad"])
        self.assertFalse(payload["KeepAlive"])
        self.assertIn("up", payload["ProgramArguments"])
        self.assertIn("--detach", payload["ProgramArguments"])

    def test_windows_wrapper_uses_detached_up(self) -> None:
        wrapper = service._write_wrapper(self.home)
        text = wrapper.read_text(encoding="ascii")
        self.assertIn("--detach", text)
        self.assertIn("loomsci", text)


if __name__ == "__main__":
    unittest.main()
