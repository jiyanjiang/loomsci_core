from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import buglog


def write_report(root: Path, number: int, status: str = "open") -> Path:
    path = root / f"{number:04d}-test.md"
    path.write_text(
        "---\n"
        f"id: BUG-{number:04d}\n"
        "title: test\n"
        f"status: {status}\n"
        "severity: P2\n"
        "surface: test\n"
        "reported: 2026-11-11\n"
        "---\n",
        encoding="utf-8",
    )
    return path


class BugLogTest(unittest.TestCase):
    def test_gate_stays_blocked_until_ten_open_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for number in range(1, 10):
                write_report(root, number)
            count, ready = buglog.gate(root)
            self.assertEqual((count, ready), (9, 0))

            write_report(root, 10)
            count, ready = buglog.gate(root)
            self.assertEqual((count, ready), (10, 1))

    def test_closed_reports_do_not_open_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for number in range(1, 11):
                write_report(root, number, status="closed")
            self.assertEqual(buglog.gate(root), (0, 0))

    def test_new_report_gets_next_id_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_report(root, 1)
            path = buglog.add_report("Ordered lists collapse", "collab", "P2", root)
            self.assertEqual(path.name, "0002-ordered-lists-collapse.md")
            text = path.read_text(encoding="utf-8")
            self.assertIn("id: BUG-0002", text)
            self.assertIn("status: open", text)
            self.assertEqual(len(buglog.open_reports(root)), 2)


if __name__ == "__main__":
    unittest.main()
