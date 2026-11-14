"""Public Python SDK for Core v0. Uses only the /v1 HTTP API."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class CoreError(RuntimeError):
    def __init__(self, error: str, status: int = 0):
        super().__init__(error)
        self.error = error
        self.status = status


class CoreClient:
    def __init__(self, base_url: str, token: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
            },
        )
        try:
            with _OPENER.open(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                payload = {"error": "http_error"}
            raise CoreError(str(payload.get("error") or "http_error"), exc.code) from None

    def health(self) -> dict:
        return self._request("GET", "/v1/health")

    def create_item(self, *, app: str, type: str, title: str = "", body: str = "",
                    metadata: dict | None = None, tags: list[str] | None = None,
                    item_id: str | None = None) -> dict:
        payload = {
            "app": app, "type": type, "title": title, "body": body,
            "metadata": metadata or {}, "tags": tags or [],
        }
        if item_id:
            payload["id"] = item_id
        return self._request("POST", "/v1/items", payload)["item"]

    def get_item(self, item_id: str) -> dict:
        return self._request("GET", "/v1/items/" + urllib.parse.quote(item_id))["item"]

    def list_items(self, *, app: str = "", type: str = "", tag: str = "",
                   limit: int = 100, offset: int = 0) -> list[dict]:
        query = urllib.parse.urlencode({
            "app": app, "type": type, "tag": tag,
            "limit": limit, "offset": offset,
        })
        return self._request("GET", "/v1/items?" + query)["items"]

    def update_item(self, item_id: str, **fields: Any) -> dict:
        return self._request("PATCH", "/v1/items/" + urllib.parse.quote(item_id), fields)["item"]

    def delete_item(self, item_id: str) -> dict:
        return self._request("DELETE", "/v1/items/" + urllib.parse.quote(item_id))

    def set_tags(self, item_id: str, tags: list[str], source: str = "ai") -> list[dict]:
        return self._request(
            "POST", f"/v1/items/{urllib.parse.quote(item_id)}/tags",
            {"tags": tags, "source": source},
        )["tags"]

    def list_tags(self, limit: int = 100) -> list[dict]:
        return self._request("GET", f"/v1/tags?limit={int(limit)}")["tags"]

    def search(self, q: str, limit: int = 50) -> list[dict]:
        query = urllib.parse.urlencode({"q": q, "limit": limit})
        return self._request("GET", "/v1/search?" + query)["items"]

    def upload_blob(self, *, filename: str, content_type: str, data: bytes,
                    item_id: str | None = None) -> dict:
        payload = {
            "filename": filename,
            "content_type": content_type,
            "content_base64": base64.b64encode(data).decode("ascii"),
        }
        if item_id:
            payload["item_id"] = item_id
        return self._request("POST", "/v1/blobs", payload)["blob"]

    def download_blob(self, blob_id: str) -> bytes:
        request = urllib.request.Request(
            self.base_url + "/v1/blobs/" + urllib.parse.quote(blob_id),
            headers={"Authorization": "Bearer " + self.token},
        )
        with _OPENER.open(request, timeout=self.timeout) as response:
            return response.read()
