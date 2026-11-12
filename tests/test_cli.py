from __future__ import annotations

import json
import socket
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cli import loomsci  # noqa: E402


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = dict(os.environ)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, "-m", "cli.loomsci", *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
    )


def _make_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE agents (id TEXT)")
        conn.execute("CREATE TABLE posts (id TEXT)")
        conn.execute("CREATE TABLE tasks (id TEXT)")
        conn.execute("INSERT INTO agents VALUES ('alice')")
        conn.commit()
    finally:
        conn.close()


class CliTest(unittest.TestCase):
    def test_home_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            result = _run(["home", "--json"], env={"LOOMSCI_HOME": str(home)})
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], str(home))
            self.assertEqual(payload["source"], "loomsci_home")

    def test_alice_init_show_and_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            env = {"LOOMSCI_HOME": str(home)}
            created = _run(
                ["alice", "init", "--owner", "owner", "--json"], env=env
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(json.loads(created.stdout)["handle"], "alice.owner")

            shown = _run(["alice", "show", "--json"], env=env)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertEqual(json.loads(shown.stdout)["handle"], "alice.owner")

            renamed = _run(
                ["alice", "rename", "--to", "assistant", "--json"], env=env
            )
            self.assertEqual(renamed.returncode, 0, renamed.stderr)
            self.assertEqual(
                json.loads(renamed.stdout)["handle"], "assistant.owner"
            )

    def test_launcher_safe_path_ignores_project_math(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            (project / "math.py").write_text("def add(a, b):\n    return a + b\n")
            env = dict(os.environ)
            env.update(
                PYTHONPATH=str(ROOT),
                PYTHONSAFEPATH="1",
                LOOMSCI_HOME=str(Path(tmp) / "home"),
            )
            result = subprocess.run(
                [sys.executable, "-m", "cli.loomsci", "home", "--json"],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("source", result.stdout)

    def test_port_preflight_detects_listener(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        try:
            self.assertFalse(loomsci._port_available("127.0.0.1", port))
        finally:
            sock.close()
        self.assertTrue(loomsci._port_available("127.0.0.1", port))

    def test_agent_list_all_and_prune(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            env = {"LOOMSCI_HOME": str(home)}
            self.assertEqual(_run(["init", "--owner", "owner"], env=env).returncode, 0)
            from core import storage

            storage.init_db(home / "data" / "data.db")
            conn = storage.connect(home / "data" / "data.db")
            storage.ensure_agent(conn, "ghost.unknown")
            conn.commit()
            conn.close()
            result = _run(["agent", "list", "--all", "--json"], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ghost.unknown", result.stdout)
            result = _run(["agent", "prune", "--json"], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ghost.unknown", result.stdout)
            self.assertIn('"dry_run": true', result.stdout)
            result = _run(["agent", "prune", "--yes", "--json"], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ghost.unknown", result.stdout)

    def test_init_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            env = {"LOOMSCI_HOME": str(home)}
            result = _run(["init", "--owner", "owner", "--json"], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["handle"], "alice.owner")
            self.assertTrue((home / "agents" / "alice" / "agent.json").is_file())

    def test_add_second_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            env = {"LOOMSCI_HOME": str(home)}
            init = _run(["alice", "init", "--owner", "owner"], env=env)
            self.assertEqual(init.returncode, 0, init.stderr)
            added = _run(
                ["agent", "add", "bob.owner", "--tool", "opencode", "--json"],
                env=env,
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            self.assertEqual(json.loads(added.stdout)["handle"], "bob.owner")
            shown = _run(
                ["alice", "show", "--short", "bob", "--json"], env=env
            )
            self.assertEqual(shown.returncode, 0, shown.stderr)
            payload = json.loads(shown.stdout)
            self.assertEqual(payload["handle"], "bob.owner")
            self.assertEqual(payload["default_tool"], "opencode")
            listed = _run(["agent", "list", "--json"], env=env)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            handles = {item["handle"] for item in json.loads(listed.stdout)["agents"]}
            self.assertEqual(handles, {"alice.owner", "bob.owner"})

    def test_export_then_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            archive = root / "export.zip"
            destination = root / "imported"
            env = {"LOOMSCI_HOME": str(home)}
            init = _run(
                ["alice", "init", "--owner", "owner", "--json"], env=env
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            exported = _run(
                ["export", "--out", str(archive), "--json"], env=env
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            imported = _run(
                ["import", str(archive), "--to", str(destination), "--json"]
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertTrue((destination / "data" / "data.db").is_file())
            self.assertTrue((destination / "agents" / "alice" / "persona.yaml").is_file())

    def test_features_json(self) -> None:
        result = _run(["features", "--json"], env={"LOOMSCI_PROFILE": "core"})
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["profile"], "core")
        self.assertLessEqual(payload["route_count"], 80)
        self.assertEqual(payload["jobs"], [])

    def test_migrate_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".taa"
            destination = root / ".loomsci"
            _make_db(source / "data.db")
            result = _run(
                [
                    "migrate",
                    "--from",
                    str(source),
                    "--to",
                    str(destination),
                    "--dry-run",
                    "--json",
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["counts"]["agents"], 1)
            self.assertFalse(destination.exists())

    def test_migrate_apply_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".taa"
            destination = root / ".loomsci"
            _make_db(source / "data.db")
            result = _run(
                [
                    "migrate",
                    "--from",
                    str(source),
                    "--to",
                    str(destination),
                    "--apply",
                    "--json",
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["dry_run"])
            self.assertTrue((destination / "data" / "data.db").is_file())
            self.assertTrue((source / "data.db").is_file())


    def test_addon_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            env = {"LOOMSCI_HOME": str(home)}
            installed = _run(["addon", "install", "ui-shell", "--json"], env=env)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            payload = json.loads(installed.stdout)
            self.assertEqual(payload["package"], "ui_shell")
            updated = _run(["addon", "update", "ui-shell", "--json"], env=env)
            self.assertEqual(updated.returncode, 0, updated.stderr)
            verified = _run(["addon", "verify", "--json"], env=env)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertTrue(json.loads(verified.stdout)["ok"])
            listed = _run(["addon", "list", "--json"], env=env)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            entry = next(item for item in json.loads(listed.stdout)["addons"] if item["name"] == "ui-shell")
            self.assertEqual(entry["installed_version"], "0.5.2")
            self.assertIn("team", json.loads(listed.stdout)["profiles"])


    def test_setup_initializes_owner_ide_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            env = {"LOOMSCI_HOME": str(home)}
            result = _run(["setup", "--owner", "owner", "--ide", "workbuddy", "--profile", "personal", "--json"], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["agent"], "alice.owner")
            self.assertEqual(payload["profile"], "personal")
            self.assertEqual(payload["ide"], "workbuddy")
            self.assertTrue((home / "agents" / "alice" / "agent.json").is_file())
            self.assertTrue((home / "agents" / "alice" / "adapters" / "workbuddy.md").is_file())
            self.assertTrue((home / "packs" / "ui_shell" / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
