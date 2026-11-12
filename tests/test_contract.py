from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage  # noqa: E402
from core.app import create_app  # noqa: E402


class ContractTest(unittest.TestCase):
    def test_schema_version_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            storage.init_db(db)
            conn = storage.connect(db)
            try:
                self.assertEqual(storage.schema_version(conn), storage.SCHEMA_VERSION)
                rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
                self.assertIn(storage.SCHEMA_VERSION, [row[0] for row in rows])
            finally:
                conn.close()

    def test_api_and_addon_contract_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            app = create_app(env={"LOOMSCI_PROFILE": "core"}, home=home)
            app.testing = True
            client = app.test_client()
            payload = client.get("/v1/version").json
            self.assertEqual(payload["api_version"], "core/1")
            self.assertEqual(payload["schema_version"], storage.SCHEMA_VERSION)
            for manifest in (ROOT / "addons").glob("*/manifest.json"):
                data = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(data.get("api"), "core/1", manifest)


if __name__ == "__main__":
    unittest.main()
