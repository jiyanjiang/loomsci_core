from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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


if __name__ == "__main__":
    unittest.main()
