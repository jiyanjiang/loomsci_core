#!/usr/bin/env python3
"""Test the minimal Core v0 API prototype."""

from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "core_v0"))

from server import create_app  # noqa: E402

HEADERS = {}


class CoreV0Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(self.home)
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + self.app.config["TOKEN"]}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_health_and_auth(self) -> None:
        self.assertEqual(self.client.get("/v1/health").status_code, 200)
        self.assertEqual(self.client.get("/v1/items").status_code, 401)
        self.assertEqual(self.client.get("/v1/items", headers=self.headers).status_code, 200)

    def test_items_tags_search_update_delete(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "PISA",
            "body": "Science communication evidence", "tags": ["PISA", "education"],
            "metadata": {"style": "research-perspective-0.1.0"},
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        item = created.json["item"]
        self.assertEqual(item["app"], "report")
        self.assertEqual({tag["tag"] for tag in item["tags"]}, {"pisa", "education"})
        listed = self.client.get("/v1/items?app=report&tag=PISA", headers=self.headers)
        self.assertEqual([row["id"] for row in listed.json["items"]], [item["id"]])
        search = self.client.get("/v1/search?q=communication", headers=self.headers)
        self.assertEqual([row["id"] for row in search.json["items"]], [item["id"]])
        updated = self.client.patch(f"/v1/items/{item['id']}", headers=self.headers,
                                    json={"title": "PISA updated", "metadata": {"x": 1}})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["item"]["title"], "PISA updated")
        tags = self.client.post(f"/v1/items/{item['id']}/tags", headers=self.headers,
                                json={"tags": ["science"]})
        self.assertEqual([tag["tag"] for tag in tags.json["tags"]], ["science"])
        deleted = self.client.delete(f"/v1/items/{item['id']}", headers=self.headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(f"/v1/items/{item['id']}", headers=self.headers).status_code, 404)

    def test_blob_upload_and_inline(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "body": "with blob",
        })
        item_id = created.json["item"]["id"]
        blob = self.client.post("/v1/blobs", headers=self.headers, json={
            "filename": "note.md", "content_type": "text/markdown",
            "content_base64": base64.b64encode(b"# hello").decode("ascii"),
            "item_id": item_id,
        })
        self.assertEqual(blob.status_code, 201, blob.get_data(as_text=True))
        blob_id = blob.json["blob"]["id"]
        inline = self.client.get(f"/v1/blobs/{blob_id}?inline=1", headers=self.headers)
        self.assertEqual(inline.status_code, 200)
        self.assertEqual(inline.json["text"], "# hello")

    def test_invalid_app_rejected(self) -> None:
        response = self.client.post("/v1/items", headers=self.headers, json={
            "app": "../bad", "type": "report.note", "body": "x",
        })
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
