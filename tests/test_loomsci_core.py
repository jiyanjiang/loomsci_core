from __future__ import annotations

import base64
import hashlib
import json
import os
import zipfile
import socket
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loomsci_core.server import create_app  # noqa: E402
from loomsci_core import store, update  # noqa: E402
from loomsci_core.version import __version__  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FormalCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(self.home)
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + self.app.config["TOKEN"]}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_items_and_search(self) -> None:
        self.assertEqual(self.client.get("/v1/health").status_code, 200)
        self.assertEqual(self.client.get("/v1/items").status_code, 401)
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "pkg",
            "body": "formal package", "tags": ["pkg"],
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        item = created.json["item"]
        self.assertEqual(item["tags"][0]["tag"], "pkg")
        found = self.client.get("/v1/search?q=formal", headers=self.headers)
        self.assertEqual([row["id"] for row in found.json["items"]], [item["id"]])

    def test_ui_and_asset_routes(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("LoomSci Core", page.get_data(as_text=True))
        self.assertNotIn("__LOOMSCI_TOKEN__", page.get_data(as_text=True))
        self.assertIn("HttpOnly", page.headers.get("Set-Cookie", ""))
        self.assertIn("SameSite=Strict", page.headers.get("Set-Cookie", ""))
        self.assertEqual(self.client.get("/v1/items").status_code, 200)
        asset = self.client.get("/assets/app.js")
        self.assertEqual(asset.status_code, 200)
        source = asset.get_data(as_text=True)
        self.assertIn("create-form", source)
        self.assertIn("loadTagsPage", source)
        self.assertIn("loadTrash", source)
        self.assertIn("item-full", source)
        self.assertIn("openFull", source)
        self.assertIn("detail-toolbar", source)
        asset.close()
        html = page.get_data(as_text=True)
        self.assertIn('id="item-view"', html)
        self.assertIn('id="tags-view"', html)
        self.assertIn('id="trash-view"', html)
        self.assertIn('id="version-view"', html)
        self.assertIn('data-view="version"', html)
        self.assertIn('id="update-current"', html)
        version = self.client.get("/v1/version")
        self.assertEqual(version.status_code, 200)
        self.assertEqual(version.json["version"], __version__)
        update_status = self.client.get("/v1/update/status")
        self.assertEqual(update_status.status_code, 200)
        self.assertEqual(update_status.json["current"], __version__)
        for path in ("/version", "/tags", "/trash", "/tools", "/settings", "/site", "/item/i-test", "/item/i-test/full"):
            route_page = self.client.get(path)
            self.assertEqual(route_page.status_code, 200, path)
            self.assertIn("LoomSci Core", route_page.get_data(as_text=True))

    def test_item_includes_blobs(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "attached",
            "body": "with file",
        })
        item = created.json["item"]
        blob = self.client.post("/v1/blobs", headers=self.headers, json={
            "filename": "note.txt", "content_type": "text/plain",
            "content_base64": base64.b64encode(b"hello").decode("ascii"),
            "item_id": item["id"],
        })
        self.assertEqual(blob.status_code, 201, blob.get_data(as_text=True))
        fetched = self.client.get("/v1/items/" + item["id"], headers=self.headers)
        self.assertEqual(fetched.json["item"]["blobs"][0]["filename"], "note.txt")
        self.assertTrue(fetched.json["item"]["blobs"][0]["hash_name"].endswith(".txt"))

    def test_tag_counts_are_app_scoped(self) -> None:
        for app in ("report", "other"):
            created = self.client.post("/v1/items", headers=self.headers, json={
                "app": app, "type": app + ".note", "title": app,
                "body": "shared tag", "tags": ["shared"],
            })
            self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        tags = {row["tag"]: row["count"] for row in self.client.get("/v1/tags", headers=self.headers).json["tags"]}
        self.assertEqual(tags["shared"], 2)
        conn = store.connect(self.home / "data" / "core.db")
        try:
            scoped = {row["tag"]: row["count"] for row in store.list_tags(conn, app="report")}
        finally:
            conn.close()
        self.assertEqual(scoped["shared"], 1)

    def test_soft_delete_trash_restore_and_blob_cleanup(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "trash me",
            "body": "delete safety", "tags": ["trash"],
        })
        item = created.json["item"]
        blob = self.client.post("/v1/blobs", headers=self.headers, json={
            "filename": "a.md", "content_type": "text/markdown",
            "content_base64": base64.b64encode(b"# a").decode("ascii"),
            "item_id": item["id"],
        }).json["blob"]
        blob_path = Path(self.app.config["BLOB_DIR"]) / blob["id"]
        self.assertTrue(blob_path.is_file())
        deleted = self.client.delete("/v1/items/" + item["id"], headers=self.headers)
        self.assertEqual(deleted.status_code, 200, deleted.get_data(as_text=True))
        self.assertFalse(deleted.json["hard"])
        listed = self.client.get("/v1/items", headers=self.headers).json["items"]
        self.assertNotIn(item["id"], [row["id"] for row in listed])
        self.assertEqual(self.client.get("/v1/search?q=delete%20safety", headers=self.headers).json["items"], [])
        tags = {row["tag"]: row["count"] for row in self.client.get("/v1/tags", headers=self.headers).json["tags"]}
        self.assertNotIn("trash", tags)
        trash = self.client.get("/v1/trash", headers=self.headers).json["items"]
        self.assertEqual([row["id"] for row in trash], [item["id"]])
        self.assertTrue(blob_path.is_file())
        restored = self.client.post("/v1/items/" + item["id"] + "/restore", headers=self.headers)
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        self.assertIn(item["id"], [row["id"] for row in self.client.get("/v1/items", headers=self.headers).json["items"]])
        self.assertEqual([row["id"] for row in self.client.get("/v1/search?q=delete%20safety", headers=self.headers).json["items"]], [item["id"]])
        tags = {row["tag"]: row["count"] for row in self.client.get("/v1/tags", headers=self.headers).json["tags"]}
        self.assertEqual(tags["trash"], 1)
        hard = self.client.delete("/v1/items/" + item["id"] + "?hard=1", headers=self.headers)
        self.assertEqual(hard.status_code, 200, hard.get_data(as_text=True))
        self.assertTrue(hard.json["hard"])
        self.assertFalse(blob_path.exists())
        self.assertEqual(self.client.get("/v1/trash", headers=self.headers).json["items"], [])

    def test_backup_and_restore(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "backup",
            "body": "portable", "tags": ["backup"],
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        backup = self.client.post("/v1/backups", headers=self.headers)
        self.assertEqual(backup.status_code, 201, backup.get_data(as_text=True))
        verified = self.client.post("/v1/backups/verify", headers=self.headers, json={
            "backup": backup.json["backup"]["path"],
        })
        self.assertEqual(verified.status_code, 200, verified.get_data(as_text=True))
        target = Path(self.tmp.name) / "restored"
        restored = self.client.post("/v1/backups/restore", headers=self.headers, json={
            "backup": backup.json["backup"]["path"], "target": str(target),
        })
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        restored_app = create_app(target)
        restored_client = restored_app.test_client()
        headers = {"Authorization": "Bearer " + restored_app.config["TOKEN"]}
        found = restored_client.get("/v1/search?q=portable", headers=headers)
        self.assertEqual([row["title"] for row in found.json["items"]], ["backup"])

    def test_release_version_consistency(self) -> None:
        from loomsci_core.version import __version__
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), __version__)
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], __version__.replace("-rc.", "rc"))

    def test_schema_version_and_migration_backup(self) -> None:
        db = self.home / "data" / "core.db"
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA user_version = 0")
        conn.commit(); conn.close()
        create_app(self.home)
        conn = sqlite3.connect(db)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        conn.close()
        self.assertTrue(list(db.parent.glob("core.db.pre-v2-*")))

    def test_future_schema_is_rejected(self) -> None:
        db = self.home / "data" / "core.db"
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA user_version = 999")
        conn.commit(); conn.close()
        with self.assertRaises(RuntimeError):
            create_app(self.home)

    def test_catalog_detection(self) -> None:
        catalog = Path(self.tmp.name) / "catalog.json"
        catalog.write_text(json.dumps({
            "format": "loomsci-catalog/1",
            "apps": [{
                "slug": "sdk-demo", "name": "Hello", "version": "0.1.0",
                "source": str(ROOT / "examples" / "hello-app"),
            }],
        }), encoding="utf-8")
        response = self.client.get("/v1/catalog?source=" + str(catalog), headers=self.headers)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json["catalog"]["apps"][0]["slug"], "sdk-demo")
        bad = self.client.get("/v1/catalog?source=" + str(Path(self.tmp.name) / "missing.json"), headers=self.headers)
        self.assertEqual(bad.status_code, 400)

    def test_update_check_download_and_state(self) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        key = Ed25519PrivateKey.generate()
        private = Path(self.tmp.name) / "private.pem"
        public = Path(self.tmp.name) / "public.pem"
        private.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        public.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        package = Path(self.tmp.name) / "release.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("loomsci_core/__init__.py", "")
        manifest = {
            "product": "loomsci_core", "version": "9.9.9", "channel": "stable",
            "min_core": "0.2.0", "url": str(package),
            "sha256": update.sha256_file(package),
        }
        manifest["signature"] = update.sign_manifest(manifest, private)
        manifest_path = Path(self.tmp.name) / "latest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        old = os.environ.get("LOOMSCI_UPDATE_PUBLIC_KEY")
        os.environ["LOOMSCI_UPDATE_PUBLIC_KEY"] = str(public)
        try:
            update.settings(self.home, manifest_url=str(manifest_path), mode="download")
            checked = update.check(self.home)
            self.assertTrue(checked["ok"], checked)
            self.assertTrue(checked["available"], checked)
            downloaded = update.download(self.home)
            self.assertTrue(downloaded["ok"], downloaded)
            self.assertEqual(downloaded["state"], "downloaded")
            self.assertTrue(Path(downloaded["downloaded"]).is_file())
            status = update.status(self.home)
            self.assertEqual(status["current"], __version__)
            self.assertEqual(status["downloaded_version"], "9.9.9")
        finally:
            if old is None:
                os.environ.pop("LOOMSCI_UPDATE_PUBLIC_KEY", None)
            else:
                os.environ["LOOMSCI_UPDATE_PUBLIC_KEY"] = old

    def test_signed_update_manifest(self) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        key = Ed25519PrivateKey.generate()
        private = Path(self.tmp.name) / "private.pem"
        public = Path(self.tmp.name) / "public.pem"
        private.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        public.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        package = Path(self.tmp.name) / "core.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("loomsci_core/__init__.py", "")
        manifest = {
            "product": "loomsci_core", "version": "0.2.1", "min_core": "0.2.0",
            "sha256": update.sha256_file(package),
        }
        manifest["signature"] = update.sign_manifest(manifest, private)
        old = os.environ.get("LOOMSCI_UPDATE_PUBLIC_KEY")
        os.environ["LOOMSCI_UPDATE_PUBLIC_KEY"] = str(public)
        try:
            self.assertEqual(update.check_manifest(manifest)["version"], "0.2.1")
            update.verify_package(package, manifest)
            bad = dict(manifest)
            bad["version"] = "0.2.2"
            with self.assertRaises(update.UpdateError):
                update.check_manifest(bad)
        finally:
            if old is None:
                os.environ.pop("LOOMSCI_UPDATE_PUBLIC_KEY", None)
            else:
                os.environ["LOOMSCI_UPDATE_PUBLIC_KEY"] = old

    def test_update_apply_rolls_back(self) -> None:
        from unittest.mock import patch
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        key = Ed25519PrivateKey.generate()
        private = Path(self.tmp.name) / "private.pem"
        public = Path(self.tmp.name) / "public.pem"
        private.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        public.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        install = Path(self.tmp.name) / "install"
        target = install / "loomsci_core"
        target.mkdir(parents=True)
        (target / "old.txt").write_text("old", encoding="utf-8")
        package = Path(self.tmp.name) / "new.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("loomsci_core/__init__.py", "")
        manifest = {
            "product": "loomsci_core", "version": "0.2.1", "min_core": "0.2.0",
            "sha256": update.sha256_file(package),
        }
        manifest["signature"] = update.sign_manifest(manifest, private)
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "rollback data",
            "body": "must survive code rollback",
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        old = os.environ.get("LOOMSCI_UPDATE_PUBLIC_KEY")
        os.environ["LOOMSCI_UPDATE_PUBLIC_KEY"] = str(public)
        try:
            with patch.object(update, "_stop", lambda _home: None), \
                 patch.object(update, "_start", side_effect=RuntimeError("health failed")):
                with self.assertRaises(update.UpdateError):
                    update.apply_package(package, manifest, home=self.home, port=8795, install_root=install)
            self.assertTrue((target / "old.txt").is_file())
            conn = sqlite3.connect(self.home / "data" / "core.db")
            try:
                title = conn.execute("SELECT title FROM items WHERE id=?", (created.json["item"]["id"],)).fetchone()
            finally:
                conn.close()
            self.assertEqual(title[0], "rollback data")
        finally:
            if old is None:
                os.environ.pop("LOOMSCI_UPDATE_PUBLIC_KEY", None)
            else:
                os.environ["LOOMSCI_UPDATE_PUBLIC_KEY"] = old

    def test_module_cli_lifecycle(self) -> None:
        port = free_port()
        command = [sys.executable, "-m", "loomsci_core", "--home", str(self.home), "--port", str(port)]
        started = subprocess.run(command + ["start", "--json"], cwd=ROOT, text=True, capture_output=True)
        if started.returncode != 0:
            logs = []
            for name in ("core.stdout.log", "core.stderr.log"):
                log = self.home / "logs" / name
                logs.append(name + ":\n" + (log.read_text(encoding="utf-8", errors="replace") if log.is_file() else "<missing>"))
            self.fail((started.stderr or "") + "\n" + "\n".join(logs))
        try:
            status = subprocess.run(command + ["status", "--json"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["running"])
        finally:
            subprocess.run(command + ["stop", "--json"], cwd=ROOT, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
