from __future__ import annotations

import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from werkzeug.serving import make_server  # noqa: E402

from cli import loomsci  # noqa: E402
from core import storage  # noqa: E402
from core.app import create_app  # noqa: E402

AGENT = "alice.jiyanjiang"
OTHER = "bob.jiyanjiang"


class CliHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name) / "home"
        app = create_app(env={"LOOMSCI_PROFILE": "core"}, home=home)
        conn = storage.connect(home / "data" / "data.db")
        storage.ensure_agent(conn, AGENT)
        storage.ensure_agent(conn, OTHER)
        conn.commit()
        conn.close()
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def _run(self, *argv: str, agent: str = AGENT) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = loomsci.main(["--url", self.base, "--as", agent, *argv])
        return code, output.getvalue()

    def _post_json(self, path: str, payload: dict, agent: str = AGENT) -> dict:
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Loomsci-Agent": agent,
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_post_then_read_advances_cursor(self) -> None:
        code, output = self._run("post", "--body", "hello from cli")
        self.assertEqual(code, 0)
        self.assertIn("posted:", output)

        code, output = self._run("read", "--json")
        self.assertEqual(code, 0)
        self.assertIn("hello from cli", output)
        code, output = self._run("read", "--since", "0", "--no-update")
        self.assertEqual(code, 0)
        self.assertIn("hello from cli", output)

        code, output = self._run("read")
        self.assertEqual(code, 0)
        self.assertIn("(no new posts)", output)

    def test_presence_register_and_list(self) -> None:
        code, output = self._run(
            "presence", "--tool", "workbuddy", "--workspace", "project"
        )
        self.assertEqual(code, 0)
        self.assertIn("presence:", output)

        code, output = self._run("presence", "--list")
        self.assertEqual(code, 0)
        self.assertIn("workbuddy", output)

    def test_memory_cli(self) -> None:
        code, output = self._run(
            "memory", "add", "--claim", "hello fact", "--evidence", "test", "--json"
        )
        self.assertEqual(code, 0, output)
        fact_id = json.loads(output)["fact"]["id"]
        code, output = self._run("memory", "list", "--json")
        self.assertEqual(code, 0, output)
        self.assertIn("hello fact", output)
        code, output = self._run(
            "memory", "review", fact_id, "--status", "approved", "--json"
        )
        self.assertEqual(code, 0, output)
        self.assertIn("approved", output)

    def test_global_as_can_follow_subcommand(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = loomsci.main(
                ["--url", self.base, "post", "--as", AGENT, "--body", "late as"]
            )
        self.assertEqual(code, 0, output.getvalue())
        code, output = self._run("read", "--json")
        self.assertEqual(code, 0)
        self.assertIn("late as", output)

    def test_search_inbox_watch_status_attachment(self) -> None:
        code, output = self._run(
            "post", "--body", "ping @bob.jiyanjiang", "--title", "Review", "--json"
        )
        self.assertEqual(code, 0, output)
        post_id = json.loads(output)["post"]["id"]

        code, output = self._run("search", "Review", "--json")
        self.assertEqual(code, 0, output)
        self.assertIn("Review", output)

        code, output = self._run("inbox", "--json", agent=OTHER)
        self.assertEqual(code, 0, output)
        self.assertIn(post_id, output)
        code, output = self._run("inbox", "--read", post_id, "--json", agent=OTHER)
        self.assertEqual(code, 0, output)
        self.assertIn('"changed": 1', output)

        code, output = self._run("status", "--json")
        self.assertEqual(code, 0, output)
        self.assertIn('"integrity": "ok"', output)

        code, output = self._run("watch", "--since", "0", "--once", "--json")
        self.assertEqual(code, 0, output)
        self.assertIn("Review", output)

        attachment = Path(self.tmp.name) / "note.txt"
        attachment.write_text("hello", encoding="utf-8")
        code, output = self._run(
            "post", "--body", "with file", "--attach", str(attachment), "--json"
        )
        self.assertEqual(code, 0, output)
        self.assertIn("attachments", output)

    def test_two_agent_task_and_handoff(self) -> None:
        code, output = self._run("task", "add", "--title", "handoff work", "--json")
        self.assertEqual(code, 0, output)
        task_id = json.loads(output)["task"]["id"]
        self.assertEqual(self._run("task", "claim", task_id, agent=AGENT)[0], 0)
        self.assertNotEqual(self._run("task", "claim", task_id, agent=OTHER)[0], 0)
        self.assertEqual(
            self._run(
                "handoff",
                "--task",
                task_id,
                "--to",
                OTHER,
                "--evidence",
                "command output",
            )[0],
            0,
        )
        code, output = self._run("read", "--json", agent=OTHER)
        self.assertEqual(code, 0)
        self.assertIn("Handoff", output)
        code, output = self._run(
            "handoff",
            "--task",
            task_id,
            "--to",
            OTHER,
            "--completed",
            "schema",
            "--next",
            "tests",
            "--evidence",
            "command output",
        )
        self.assertEqual(code, 0, output)
        self.assertIn("handoff posted", output)


if __name__ == "__main__":
    unittest.main()
