from __future__ import annotations

import socket
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import core_runtime  # noqa: E402


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class CoreRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.port = free_port()
        self.started = False

    def tearDown(self) -> None:
        if self.started:
            core_runtime.stop(self.home)
        self.tmp.cleanup()

    def test_detached_start_status_and_stop(self) -> None:
        result = core_runtime.start(
            self.home, port=self.port, python_path=ROOT, timeout=25
        )
        self.started = True
        self.assertTrue(result["running"])
        self.assertEqual(result["health"]["version"], (ROOT / "VERSION").read_text().strip())

        state = core_runtime.status(self.home)
        self.assertTrue(state["ok"])
        self.assertEqual(state["port"], self.port)

        stopped = core_runtime.stop(self.home)
        self.started = False
        self.assertTrue(stopped["stopped"])
        self.assertFalse(core_runtime.status(self.home)["running"])

    def test_second_start_is_idempotent(self) -> None:
        first = core_runtime.start(
            self.home, port=self.port, python_path=ROOT, timeout=25
        )
        self.started = True
        second = core_runtime.start(
            self.home, port=self.port, python_path=ROOT, timeout=25
        )
        self.assertTrue(second.get("already_running"))
        self.assertEqual(first["pid"], second["pid"])

    def test_primary_url_falls_back_to_core(self) -> None:
        self.assertEqual(
            core_runtime.primary_url(self.home, core_port=self.port),
            f"http://127.0.0.1:{self.port}/app/posts",
        )


if __name__ == "__main__":
    unittest.main()
