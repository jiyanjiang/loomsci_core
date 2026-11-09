from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PublicTreeTest(unittest.TestCase):
    def test_public_tree_is_sanitized(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_public_tree.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
