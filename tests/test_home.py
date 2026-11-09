from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.home import (  # noqa: E402
    HomeConflict,
    HomeError,
    apply_migration,
    ensure_layout,
    migration_plan,
    resolve_home,
)


def _make_db(path: Path, agents: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE agents (id TEXT)")
        conn.execute("CREATE TABLE posts (id TEXT)")
        conn.execute("CREATE TABLE tasks (id TEXT)")
        for index in range(agents):
            conn.execute("INSERT INTO agents VALUES (?)", (f"agent-{index}",))
        conn.execute("INSERT INTO posts VALUES ('post-1')")
        conn.commit()
    finally:
        conn.close()


class HomeResolutionTest(unittest.TestCase):
    def test_explicit_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".loomsci").mkdir()
            resolution = resolve_home(
                explicit=root / "custom",
                env={"LOOMSCI_HOME": str(root / "env")},
                home_dir=root,
            )
            self.assertEqual(resolution.path, root / "custom")
            self.assertEqual(resolution.source, "explicit")

    def test_env_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolution = resolve_home(
                env={"LOOMSCI_HOME": str(root / "new"), "TAA_HOME": str(root / "old")},
                home_dir=root,
            )
            self.assertEqual(resolution.path, root / "new")
            self.assertFalse(resolution.legacy)

    def test_legacy_env_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolution = resolve_home(
                env={"TAA_HOME": str(root / "old")},
                home_dir=root,
            )
            self.assertTrue(resolution.legacy)

    def test_default_when_nothing_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolution = resolve_home(env={}, home_dir=root)
            self.assertEqual(resolution.path, root / ".loomsci")
            self.assertFalse(resolution.needs_migration)

    def test_legacy_only_needs_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".taa").mkdir()
            resolution = resolve_home(env={}, home_dir=root)
            self.assertEqual(resolution.path, root / ".taa")
            self.assertTrue(resolution.needs_migration)

    def test_both_homes_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".loomsci").mkdir()
            (root / ".taa").mkdir()
            with self.assertRaises(HomeConflict):
                resolve_home(env={}, home_dir=root)


class LayoutAndMigrationTest(unittest.TestCase):
    def test_ensure_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layout = ensure_layout(Path(tmp) / "home")
            self.assertTrue(layout.db.parent.is_dir())
            self.assertTrue(layout.agents.is_dir())
            self.assertTrue(layout.packs.is_dir())
            self.assertTrue(layout.port_file.parent.is_dir())

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".taa"
            destination = root / ".loomsci"
            _make_db(source / "data.db")
            (source / "agents" / "alice").mkdir(parents=True)
            (source / "agents" / "alice" / "agent.json").write_text("{}", encoding="utf-8")
            (source / "config.toml").write_text("profile = 'core'\n", encoding="utf-8")

            plan = migration_plan(source, destination)
            self.assertEqual(plan.counts["agents"], 2)
            result = apply_migration(plan, dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertFalse(destination.exists())

    def test_apply_copies_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".taa"
            destination = root / ".loomsci"
            _make_db(source / "data.db")
            (source / "agents" / "alice").mkdir(parents=True)
            (source / "agents" / "alice" / "agent.json").write_text("{}", encoding="utf-8")
            (source / "config.toml").write_text("profile = 'core'\n", encoding="utf-8")

            plan = migration_plan(source, destination)
            result = apply_migration(plan, dry_run=False)
            self.assertFalse(result["dry_run"])
            self.assertTrue((destination / "data" / "data.db").is_file())
            self.assertTrue((destination / "agents" / "alice" / "agent.json").is_file())
            self.assertTrue((destination / "config.toml").is_file())
            self.assertTrue((source / "data.db").is_file())

            conn = sqlite3.connect(destination / "data" / "data.db")
            try:
                self.assertEqual(conn.execute("SELECT count(*) FROM agents").fetchone()[0], 2)
            finally:
                conn.close()

    def test_refuses_non_empty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".taa"
            destination = root / ".loomsci"
            _make_db(source / "data.db")
            destination.mkdir()
            (destination / "keep.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(HomeError):
                migration_plan(source, destination)


if __name__ == "__main__":
    unittest.main()
