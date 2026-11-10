from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from addons.research import store  # noqa: E402


class ResearchStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "research"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_workspace_versions_sources_facts_and_gate(self) -> None:
        first = store.new("test topic", root=self.root)
        second = store.new("test topic", root=self.root)
        self.assertEqual(first["code"], second["code"])
        self.assertEqual(second["version"], "v2")
        ref = f"{first['code']}@v1"
        store.add_source(self.root, ref, url="https://www.gov.cn/a", title="test topic official")
        store.add_source(self.root, ref, url="https://example.org/b", title="test topic second")
        store.add_fact(self.root, ref, claim="a", url="https://www.gov.cn/a", quote="q")
        store.write_draft(
            self.root,
            ref,
            "test topic says [S1] and https://example.org/b",
        )
        result = store.check(self.root, ref)
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["domain_count"], 2)
        self.assertGreaterEqual(result["cited_count"], 2)

    def test_gate_rejects_single_domain(self) -> None:
        item = store.new("single domain", root=self.root)
        ref = f"{item['code']}@v1"
        store.add_source(self.root, ref, url="https://www.gov.cn/a", title="single domain")
        store.write_draft(self.root, ref, "single domain [S1] https://www.gov.cn/a")
        result = store.check(self.root, ref)
        self.assertFalse(result["ok"])
        self.assertTrue(any("域名" in reason for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
