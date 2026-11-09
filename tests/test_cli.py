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
