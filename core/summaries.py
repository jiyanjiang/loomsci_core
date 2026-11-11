"""Derived post summaries: local fallback plus optional DeepSeek generation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from core import storage

SHORT_POST_MAX = 800
SUMMARY_MIN = 300
SUMMARY_MAX = 500
SUMMARY_TARGET = 400
CHAT_URL = os.environ.get(
    "DEEPSEEK_CHAT_URL", "https://api.deepseek.com/chat/completions"
)
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
_SENTENCE_END = re.compile(r"[。！？!?]|\.(?=\s|$)")
_MARKDOWN = (
    (re.compile(r"```.*?```", re.S), " "),
    (re.compile(r"^\s{0,3}#{1,6}\s+", re.M), ""),
    (re.compile(r"!\[([^\]]*)\]\([^)]*\)"), r"\1"),
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),
    (re.compile(r"[*_~`>#-]+"), " "),
    (re.compile(r"\s+"), " "),
)


def needs_summary(body: str) -> bool:
    return len(str(body or "")) > SHORT_POST_MAX


def _plain(text: str) -> str:
    value = str(text or "")
    for pattern, replacement in _MARKDOWN:
        value = pattern.sub(replacement, value)
    return value.strip()


def _clip(text: str, limit: int = SUMMARY_MAX) -> str:
    value = _plain(text)
    if len(value) <= limit:
        return value
    cut = value[:limit]
    matches = list(_SENTENCE_END.finditer(cut))
    if matches and matches[-1].end() >= SUMMARY_MIN:
        return cut[: matches[-1].end()].strip()
    return cut.rsplit(" ", 1)[0].strip() if " " in cut[-80:] else cut.strip()


def fallback(body: str) -> str:
    value = _plain(body)
    if len(value) <= SUMMARY_MAX:
        return value
    cut = value[:SUMMARY_MAX]
    matches = list(_SENTENCE_END.finditer(cut))
    if matches and matches[-1].end() >= SUMMARY_MIN:
        return cut[: matches[-1].end()].strip()
    return cut.rsplit(" ", 1)[0].strip() if " " in cut[-80:] else cut.strip()


def _source_hash(body: str) -> str:
    return hashlib.sha256(str(body or "").encode("utf-8")).hexdigest()


def _settings(home: Path | None) -> tuple[str, str]:
    """Return (mode, key); mode is ai or extractive."""
    if home is None:
        return "extractive", ""
    path = Path(home) / "config.yaml"
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            import yaml

            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            data = {}
    posts = data.get("posts") if isinstance(data.get("posts"), dict) else {}
    summary = posts.get("summary") if isinstance(posts.get("summary"), dict) else {}
    mode = str(summary.get("mode") or "ai").strip().lower()
    llm = data.get("llm") if isinstance(data.get("llm"), dict) else {}
    key = str(llm.get("deepseek_api_key") or "").strip()
    return ("ai" if mode == "ai" and key else "extractive"), key


def enqueue_for_post(
    conn,
    *,
    post_id: str,
    body: str,
    home: str | Path | None = None,
) -> None:
    if not needs_summary(body):
        return
    mode, _ = _settings(Path(home).expanduser() if home else None)
    status = "pending" if mode == "ai" else "fallback"
    stamp = storage.now()
    conn.execute(
        "INSERT OR IGNORE INTO post_summaries"
        "(post_id, summary, status, model, source_hash, error, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            post_id,
            fallback(body),
            status,
            "extractive" if status == "fallback" else None,
            _source_hash(body),
            None,
            stamp,
            stamp,
        ),
    )
    conn.commit()


def _prompt(body: str) -> str:
    return (
        f"Summarize this research post in about {SUMMARY_TARGET} characters "
        f"(between {SUMMARY_MIN} and {SUMMARY_MAX}), in the dominant "
        "language of the post. Preserve the topic, claims, evidence, decisions, "
        "next actions, and uncertainty. Do not add facts. Do not use Markdown "
        "headings or a title. Return only the summary.\n\n" + body
    )


def _generate_ai(body: str, key: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "temperature": 0.3,
            "max_tokens": 800,
            "messages": [
                {"role": "system", "content": "You write faithful, compact research summaries."},
                {"role": "user", "content": _prompt(body)},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        CHAT_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("empty model response")
    text = str((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise ValueError("empty summary")
    return _clip(text)


def generate_one(conn, *, post_id: str, home: str | Path | None = None) -> bool:
    row = conn.execute(
        "SELECT p.id, p.body, s.status FROM posts p "
        "JOIN post_summaries s ON s.post_id = p.id WHERE p.id=?",
        (post_id,),
    ).fetchone()
    if row is None or row["status"] not in {"pending", "failed"}:
        return False
    body = str(row["body"] or "")
    mode, key = _settings(Path(home).expanduser() if home else None)
    stamp = storage.now()
    if mode != "ai":
        conn.execute(
            "UPDATE post_summaries SET summary=?, status='fallback', model='extractive', "
            "error=NULL, updated_at=? WHERE post_id=?",
            (fallback(body), stamp, post_id),
        )
        conn.commit()
        return True
    try:
        summary = _generate_ai(body, key)
        if len(summary) < SUMMARY_MIN:
            summary = fallback(body)
            status = "fallback"
            model = "extractive"
        else:
            status = "ready"
            model = MODEL
        conn.execute(
            "UPDATE post_summaries SET summary=?, status=?, model=?, error=NULL, "
            "source_hash=?, updated_at=? WHERE post_id=?",
            (summary, status, model, _source_hash(body), stamp, post_id),
        )
    except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
        conn.execute(
            "UPDATE post_summaries SET summary=?, status='failed', error=?, updated_at=? "
            "WHERE post_id=?",
            (fallback(body), str(exc)[:200], stamp, post_id),
        )
    conn.commit()
    return True


class SummaryWorker:
    def __init__(self, db_path: str | Path, home: str | Path | None, interval: float = 2.0):
        self.db_path = str(db_path)
        self.home = home
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="loomsci-summary", daemon=True)

    def start(self) -> "SummaryWorker":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                conn = storage.connect(self.db_path)
                try:
                    rows = conn.execute(
                        "SELECT post_id FROM post_summaries "
                        "WHERE status = 'pending' ORDER BY created_at LIMIT 1"
                    ).fetchall()
                    for row in rows:
                        generate_one(conn, post_id=row["post_id"], home=self.home)
                finally:
                    conn.close()
            except Exception:  # noqa: BLE001 - worker must survive transient failures
                pass
            self._stop.wait(self.interval)


def start_worker(db_path: str | Path, home: str | Path | None) -> SummaryWorker:
    worker = SummaryWorker(db_path, home)
    return worker.start()
