"""Read-only asset inventory for the P2.5 backup boundary.

This module deliberately does not create or delete files. It classifies the
home into authored/generated assets, third-party references, derived/cache
data, and secrets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from core.home import ensure_layout

SKIP_PARTS = {
    ".git", ".cache", ".DS_Store", "__pycache__", "node_modules", "venv",
    ".venv", "core", "cli", "docs", "scripts", "releases", "logs", "runtime",
    "tmp", "temp", "dist", "build",
}
SECRET_NAMES = {".key", ".token", ".pwprofile", ".env", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
REFERENCE_SUFFIXES = {
    ".pdf", ".epub", ".mobi", ".djvu", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".csv", ".parquet",
    ".ipynb",
}
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".py",
    ".js", ".ts", ".tsx", ".jsx", ".css", ".html", ".htm", ".sql", ".sh",
}
SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("generic_secret", re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*[\"']?[^\s\"']{8,}")),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _is_secret_name(path: Path) -> bool:
    return path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES


def _attachment_suffixes(home: Path) -> dict[str, str]:
    db = home / "data" / "data.db"
    if not db.is_file():
        return {}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        rows = conn.execute("SELECT id, filename, content_type FROM attachments").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        if conn is not None:
            conn.close()
    result = {}
    for attachment_id, filename, content_type in rows:
        suffix = Path(str(filename or "")).suffix.lower()
        if suffix in REFERENCE_SUFFIXES or str(content_type or "").lower() in {
            "application/pdf", "application/epub+zip", "application/zip",
            "application/octet-stream",
        }:
            result[str(attachment_id)] = suffix or ".bin"
    return result


def _category(path: Path, home: Path, attachment_suffixes: dict[str, str] | None = None) -> tuple[str, str]:
    rel = path.relative_to(home)
    suffix = path.suffix.lower()
    if _is_secret_name(path):
        return "secret", "secret filename"
    if path == home / "config.yaml":
        return "secret", "configuration may contain credentials"
    if path == home / "data" / "data.db":
        return "asset", "SQLite database"
    if rel.parts[:1] == ("agents",):
        return "asset", "agent persona"
    if rel.parts[:2] == ("data", "blobs"):
        suffix = (attachment_suffixes or {}).get(path.name, suffix)
        if suffix in REFERENCE_SUFFIXES:
            return "reference", "third-party binary"
        return "asset", "attachment"
    if rel.parts[:1] in {("assets",), ("programs",)}:
        return "asset", "user/AI program asset"
    if rel.parts[:1] == ("packs",):
        if len(rel.parts) >= 3 and rel.parts[2] == "data":
            if any(part in {"thumbs", "thumbnails", "cache", "ocr"} for part in rel.parts):
                return "derived", "generated cache"
            if suffix in REFERENCE_SUFFIXES:
                return "reference", "third-party binary"
            return "asset", "add-on data"
        return "excluded", "add-on code"
    if rel.parts[:1] == ("data",):
        return "excluded", "data directory"
    return "excluded", "not a backup asset"


def _walk(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        return
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_PARTS and not name.startswith(".")]
        for name in files:
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            yield path


def _iter_candidates(home: Path) -> Iterator[Path]:
    seen: set[Path] = set()
    roots = [
        home / "data" / "data.db",
        home / "config.yaml",
        home / "agents",
        home / "data" / "blobs",
        home / "assets",
        home / "programs",
    ]
    packs = home / "packs"
    if packs.is_dir():
        roots.extend(path / "data" for path in packs.iterdir() if path.is_dir())
    for root in roots:
        if root.is_file():
            paths = [root]
        else:
            paths = _walk(root)
        for path in paths:
            if path in seen or not _inside(path, home):
                continue
            seen.add(path)
            yield path


def _scan_text(text: str, location: str) -> list[dict[str, str]]:
    hits = []
    for kind, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append({"kind": kind, "location": location})
    return hits


def _scan_file(path: Path, home: Path) -> list[dict[str, str]]:
    rel = path.relative_to(home).as_posix()
    if _is_secret_name(path) or path == home / "config.yaml":
        return [{"kind": "secret_file", "location": rel}]
    if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 1024 * 1024:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return _scan_text(text, rel)


def _scan_db(db: Path) -> list[dict[str, str]]:
    if not db.is_file():
        return []
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        hits = []
        for table, columns in {
            "posts": ("id", "title", "body"),
            "tasks": ("id", "title", "description", "acceptance"),
            "facts": ("id", "claim", "evidence", "source"),
        }.items():
            try:
                rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                for column, value in zip(columns, row):
                    if isinstance(value, str):
                        hits.extend(_scan_text(value, f"{table}/{row[0]}/{column}"))
        return hits
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def inspect(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    summary = {
        "assets": {"files": 0, "bytes": 0},
        "references": {"files": 0, "bytes": 0},
        "derived": {"files": 0, "bytes": 0},
        "excluded": {"files": 0, "bytes": 0},
        "secrets": {"files": 0, "bytes": 0, "hits": 0},
    }
    samples: dict[str, list[dict[str, Any]]] = {key: [] for key in summary}
    secret_hits: list[dict[str, str]] = []
    hashes: dict[str, list[dict[str, Any]]] = {}

    attachment_suffixes = _attachment_suffixes(home)
    for path in _iter_candidates(home):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        category, reason = _category(path, home, attachment_suffixes)
        key = {"asset": "assets", "reference": "references", "derived": "derived", "secret": "secrets"}.get(category, "excluded")
        summary[key]["files"] += 1
        summary[key]["bytes"] += size
        if key != "secrets" and len(samples[key]) < 50:
            samples[key].append({
                "path": path.relative_to(home).as_posix(),
                "bytes": size,
                "reason": reason,
            })
        hits = _scan_file(path, home)
        if hits:
            summary["secrets"]["hits"] += len(hits)
            if key != "secrets":
                summary["secrets"]["files"] += 1
            secret_hits.extend(hits[:20])
        if category == "asset" and path.suffix.lower() not in TEXT_SUFFIXES:
            digest = _sha256(path)
            hashes.setdefault(digest, []).append({
                "path": path.relative_to(home).as_posix(),
                "bytes": size,
            })

    db_hits = _scan_db(home / "data" / "data.db")
    if db_hits:
        summary["secrets"]["hits"] += len(db_hits)
        secret_hits.extend(db_hits[:50])

    duplicates = []
    reclaimable = 0
    for digest, files in hashes.items():
        if len(files) > 1:
            reclaimable += sum(item["bytes"] for item in files[:-1])
            duplicates.append({"sha256": digest, "count": len(files), "bytes": sum(item["bytes"] for item in files), "files": files[:20]})

    warnings = []
    if summary["references"]["files"]:
        warnings.append("third-party binaries are indexed but excluded from the asset backup")
    if summary["derived"]["files"]:
        warnings.append("derived/cache files are excluded")
    if secret_hits:
        warnings.append("secret-like content found; backup export must be blocked or redacted")

    return {
        "ok": True,
        "home": str(home),
        "summary": summary,
        "duplicates": duplicates,
        "reclaimable_bytes": reclaimable,
        "secret_hits": secret_hits,
        "samples": samples,
        "warnings": warnings,
    }


BUNDLE_FORMAT = "loomsci_asset_bundle"
BUNDLE_VERSION = 1
BACKUP_EXCLUDED_TOP = {
    "core", "cli", "docs", "scripts", "releases", "venv", "logs", "runtime",
    "bin", "node_modules", "__pycache__", ".git", ".cache",
}


class BackupError(RuntimeError):
    pass


def _safe_name(value: str, fallback: str = "file") -> str:
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(value or "")).strip() or fallback
    return name[:120]


def _read_attachment_rows(db: Path) -> list[dict[str, Any]]:
    if not db.is_file():
        return []
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM attachments ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def _md_front_matter(values: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        text = str(value).replace("\n", " ")
        lines.append(f"{key}: {text}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _markdown_files(db: Path, attachments: dict[str, dict[str, Any]]) -> dict[str, str]:
    files = {}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        posts = conn.execute("SELECT * FROM posts ORDER BY seq").fetchall()
        for row in posts:
            item = dict(row)
            links = []
            for attachment_id in [a["id"] for a in _read_attachment_rows(db) if a.get("post_id") == item["id"]]:
                meta = attachments.get(attachment_id)
                if meta:
                    links.append(f"- [{meta['filename']}](../../{meta['path']})")
            body = _md_front_matter({
                "id": item["id"], "seq": item["seq"], "thread_id": item.get("thread_id"),
                "parent_id": item.get("parent_id"), "author": item.get("author"),
                "kind": item.get("kind"), "title": item.get("title"),
                "created_at": item.get("created_at"),
            }) + (item.get("body") or "") + ("\n\n## Attachments\n" + "\n".join(links) if links else "") + "\n"
            files[f"md/posts/{int(item['seq']):06d}-{_safe_name(item['id'])}.md"] = body
        tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()
        for row in tasks:
            item = dict(row)
            body = _md_front_matter({
                "id": item["id"], "status": item.get("status"),
                "assigned_to": item.get("assigned_to"), "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }) + f"# {item.get('title') or item['id']}\n\n{item.get('description') or ''}\n\n## Acceptance\n\n{item.get('acceptance') or ''}\n"
            files[f"md/tasks/{_safe_name(item['id'])}.md"] = body
        facts = conn.execute("SELECT * FROM facts ORDER BY created_at").fetchall()
        for row in facts:
            item = dict(row)
            body = _md_front_matter({
                "id": item["id"], "project": item.get("project"),
                "status": item.get("status"), "source": item.get("source"),
                "created_at": item.get("created_at"),
            }) + f"# {item.get('claim')}\n\n{item.get('evidence') or ''}\n"
            files[f"md/facts/{_safe_name(item['id'])}.md"] = body
        return files
    except sqlite3.Error:
        return files
    finally:
        if conn is not None:
            conn.close()


def _snapshot_db(source: Path, target: Path) -> None:
    src = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()


def _redact_text(text: str) -> str:
    for _kind, pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _drop_attachment_rows(db: Path, ids: set[str]) -> None:
    if not ids:
        return
    conn = sqlite3.connect(db)
    try:
        conn.executemany("DELETE FROM attachments WHERE id=?", [(item,) for item in ids])
        conn.commit()
    finally:
        conn.close()


def _redact_db(db: Path) -> int:
    count = 0
    conn = sqlite3.connect(db)
    try:
        targets = {
            "posts": ("title", "body"),
            "tasks": ("title", "description", "acceptance"),
            "facts": ("claim", "evidence", "source"),
        }
        for table, columns in targets.items():
            try:
                rows = conn.execute(f"SELECT rowid, {', '.join(columns)} FROM {table}").fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                values = []
                changed = False
                for value in row[1:]:
                    if isinstance(value, str):
                        redacted = _redact_text(value)
                        changed = changed or redacted != value
                        values.append(redacted)
                    else:
                        values.append(value)
                if changed:
                    assignments = ", ".join(f"{column}=?" for column in columns)
                    conn.execute(f"UPDATE {table} SET {assignments} WHERE rowid=?", (*values, row[0]))
                    count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def _included_text_files(home: Path) -> Iterator[Path]:
    for root in (home / "agents", home / "assets", home / "programs"):
        for path in _walk(root):
            if _is_secret_name(path):
                continue
            yield path
    packs = home / "packs"
    if packs.is_dir():
        for pack in packs.iterdir():
            data = pack / "data"
            if not data.is_dir():
                continue
            for path in _walk(data):
                if any(part in {"thumbs", "thumbnails", "cache", "ocr"} for part in path.relative_to(home).parts):
                    continue
                if _is_secret_name(path):
                    continue
                yield path


def _included_secret_hits(home: Path) -> list[dict[str, str]]:
    hits = []
    for path in _included_text_files(home):
        hits.extend(_scan_file(path, home))
    db = home / "data" / "data.db"
    hits.extend(_scan_db(db))
    return hits


def _zip_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> dict[str, Any]:
    zf.writestr(name, data)
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def create(home: str | Path, out_path: str | Path, *, redact: bool = False, allow_secrets: bool = False) -> dict[str, Any]:
    home = Path(home).expanduser()
    out = Path(out_path).expanduser()
    db = home / "data" / "data.db"
    if not db.is_file():
        raise BackupError("database not found")
    hits = _included_secret_hits(home)
    if hits and not redact and not allow_secrets:
        locations = ", ".join(sorted({hit["location"] for hit in hits})[:8])
        raise BackupError(f"secret-like content found; use --redact or --allow-secrets: {locations}")

    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".loomsci-backup-", suffix=".zip", dir=out.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    files: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    attachments_meta: dict[str, dict[str, Any]] = {}
    asset_paths: dict[str, str] = {}
    try:
        with tempfile.TemporaryDirectory() as workspace:
            snapshot = Path(workspace) / "data.db"
            _snapshot_db(db, snapshot)
            redacted_rows = _redact_db(snapshot) if redact and hits else 0
            attachment_rows = _read_attachment_rows(snapshot)
            for row in attachment_rows:
                attachment_id = row["id"]
                filename = _safe_name(row.get("filename") or "file")
                stem = Path(filename).stem or "file"
                suffix = Path(filename).suffix.lower()
                blob = home / "data" / "blobs" / attachment_id
                if not blob.is_file():
                    continue
                content_type = str(row.get("content_type") or "").lower()
                is_reference = suffix in REFERENCE_SUFFIXES or content_type in {
                    "application/pdf", "application/epub+zip", "application/zip",
                    "application/octet-stream",
                }
                if is_reference:
                    references.append({
                        "attachment_id": attachment_id,
                        "filename": filename,
                        "content_type": content_type,
                        "bytes": int(row.get("bytes") or blob.stat().st_size),
                        "sha256": row.get("sha256"),
                        "reason": "third_party_reference",
                    })
                    continue
                digest = _sha256(blob)
                if digest not in asset_paths:
                    asset_paths[digest] = f"assets/{digest}/{stem}{suffix}"
                attachments_meta[attachment_id] = {
                    "filename": filename,
                    "content_type": content_type,
                    "bytes": blob.stat().st_size,
                    "sha256": digest,
                    "path": asset_paths[digest],
                }

            reference_ids = {item["attachment_id"] for item in references}
            _drop_attachment_rows(snapshot, reference_ids)

            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for name, data in _markdown_files(snapshot, attachments_meta).items():
                    files.append(_zip_bytes(zf, name, data.encode("utf-8")))
                files.append(_zip_bytes(zf, "data/data.db", snapshot.read_bytes()))

                for attachment_id, meta in attachments_meta.items():
                    blob = home / "data" / "blobs" / attachment_id
                    asset_path = meta["path"]
                    if any(item["path"] == asset_path for item in files):
                        continue
                    files.append(_zip_bytes(zf, asset_path, blob.read_bytes()))

                for path in _included_text_files(home):
                    rel = path.relative_to(home).as_posix()
                    if path.suffix.lower() not in TEXT_SUFFIXES:
                        continue
                    data = path.read_bytes()
                    if redact and hits:
                        text = data.decode("utf-8", errors="replace")
                        data = _redact_text(text).encode("utf-8")
                    files.append(_zip_bytes(zf, rel, data))

                # Preserve agent/pack data that is not text/code (media under packs).
                for root in (home / "agents", home / "assets", home / "programs"):
                    for path in _walk(root):
                        if _is_secret_name(path) or path.suffix.lower() in TEXT_SUFFIXES:
                            continue
                        rel = path.relative_to(home).as_posix()
                        files.append(_zip_bytes(zf, rel, path.read_bytes()))
                packs = home / "packs"
                if packs.is_dir():
                    for pack in packs.iterdir():
                        data_root = pack / "data"
                        if not data_root.is_dir():
                            continue
                        for path in _walk(data_root):
                            rel = path.relative_to(home).as_posix()
                            if any(part in {"thumbs", "thumbnails", "cache", "ocr"} for part in Path(rel).parts):
                                excluded.append({"path": rel, "reason": "derived/cache"})
                                continue
                            if _is_secret_name(path):
                                excluded.append({"path": rel, "reason": "secret filename"})
                                continue
                            if path.suffix.lower() in TEXT_SUFFIXES:
                                continue
                            files.append(_zip_bytes(zf, rel, path.read_bytes()))

                for name in ("core", "cli", "docs", "scripts", "releases", "venv", "logs", "runtime", "bin"):
                    if (home / name).exists():
                        excluded.append({"path": name + "/", "reason": "runtime/code"})

                policy = {
                    "assets": ["data.db", "agents", "assets", "programs", "packs/*/data", "generated media"],
                    "references": "metadata only; third-party binaries excluded",
                    "derived": "excluded",
                    "secrets": "never included; blocked or redacted",
                }
                counts = {
                    "files": len(files),
                    "assets": sum(1 for item in files if item["path"].startswith("assets/")),
                    "markdown": sum(1 for item in files if item["path"].startswith("md/")),
                    "references": len(references),
                    "excluded": len(excluded),
                    "redacted_rows": redacted_rows,
                }
                manifest = {
                    "format": BUNDLE_FORMAT,
                    "version": BUNDLE_VERSION,
                    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "product_version": (home / "VERSION").read_text(encoding="utf-8").strip() if (home / "VERSION").is_file() else "",
                    "counts": counts,
                    "files": files,
                    "redacted": bool(redact and hits),
                    "allow_secrets": bool(allow_secrets),
                }
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                zf.writestr("policy.json", json.dumps(policy, ensure_ascii=False, indent=2))
                zf.writestr("references.json", json.dumps(references, ensure_ascii=False, indent=2))
                zf.writestr("excluded.json", json.dumps(excluded, ensure_ascii=False, indent=2))
                zf.writestr("attachments.json", json.dumps(attachments_meta, ensure_ascii=False, indent=2))
        os.replace(tmp, out)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return {"ok": True, "path": str(out), "counts": counts, "sha256": _sha256(out), "bytes": out.stat().st_size}


def _bundle_manifest(zf: zipfile.ZipFile) -> dict[str, Any]:
    try:
        data = json.loads(zf.read("manifest.json").decode("utf-8"))
    except (KeyError, ValueError, OSError) as exc:
        raise BackupError("invalid backup manifest") from exc
    if data.get("format") != BUNDLE_FORMAT or int(data.get("version") or 0) != BUNDLE_VERSION:
        raise BackupError("unsupported backup format")
    return data


def inspect_bundle(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser()
    if not source.is_file():
        raise BackupError("backup file not found")
    try:
        with zipfile.ZipFile(source) as zf:
            manifest = _bundle_manifest(zf)
            names = set(zf.namelist())
            if len(names) > 20_000:
                raise BackupError("too many bundle members")
            for item in manifest.get("files", []):
                name = item.get("path")
                if not name or name not in names:
                    raise BackupError(f"missing bundle member: {name}")
                data = zf.read(name)
                if hashlib.sha256(data).hexdigest() != item.get("sha256"):
                    raise BackupError(f"hash mismatch: {name}")
            return {
                "ok": True,
                "path": str(source),
                "bytes": source.stat().st_size,
                "counts": manifest.get("counts", {}),
                "redacted": bool(manifest.get("redacted")),
                "allow_secrets": bool(manifest.get("allow_secrets")),
                "created_at": manifest.get("created_at"),
                "files": len(manifest.get("files", [])),
            }
    except zipfile.BadZipFile as exc:
        raise BackupError("invalid backup zip") from exc


def _safe_member(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name or ":" in name.split("/")[0]:
        return False
    parts = Path(name).parts
    return ".." not in parts


def restore_bundle(path: str | Path, destination: str | Path, *, apply: bool = False) -> dict[str, Any]:
    source = Path(path).expanduser()
    dest = Path(destination).expanduser()
    if not source.is_file():
        raise BackupError("backup file not found")
    inspect_bundle(source)
    with zipfile.ZipFile(source) as zf:
        manifest = _bundle_manifest(zf)
        names = zf.namelist()
        for name in names:
            if not _safe_member(name):
                raise BackupError(f"unsafe bundle member: {name}")
        if dest.exists() and any(dest.iterdir()):
            raise BackupError(f"destination is not empty: {dest}")
        attachments = json.loads(zf.read("attachments.json").decode("utf-8")) if "attachments.json" in names else {}
        if not apply:
            return {
                "ok": True, "dry_run": True, "destination": str(dest),
                "counts": manifest.get("counts", {}), "attachments": len(attachments),
            }

        ensure_layout(dest)
        data_dir = dest / "data"
        blobs = data_dir / "blobs"
        blobs.mkdir(parents=True, exist_ok=True)
        (data_dir / "data.db").write_bytes(zf.read("data/data.db"))
        materialized: dict[str, Path] = {}
        for attachment_id, meta in attachments.items():
            asset = meta.get("path")
            if not asset or asset not in names:
                continue
            target = blobs / _safe_name(attachment_id)
            if asset in materialized:
                try:
                    os.link(materialized[asset], target)
                    continue
                except OSError:
                    pass
            target.write_bytes(zf.read(asset))
            materialized[asset] = target
            try:
                target.chmod(0o600)
            except OSError:
                pass
        for name in names:
            if name.startswith("agents/") or name.startswith("packs/"):
                relative = Path(name)
                target = dest / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
        return {
            "ok": True, "dry_run": False, "destination": str(dest),
            "counts": manifest.get("counts", {}), "attachments": len(attachments),
        }


def verify_bundle(path: str | Path) -> dict[str, Any]:
    summary = inspect_bundle(path)
    source = Path(path).expanduser()
    with zipfile.ZipFile(source) as zf:
        raw = zf.read("data/data.db")
        with tempfile.TemporaryDirectory() as workspace:
            db = Path(workspace) / "data.db"
            db.write_bytes(raw)
            conn = sqlite3.connect(db)
            try:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                counts = {}
                for table in ("posts", "tasks", "facts", "attachments"):
                    try:
                        counts[table] = int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
                    except sqlite3.Error:
                        counts[table] = 0
            finally:
                conn.close()
        attachments = json.loads(zf.read("attachments.json").decode("utf-8")) if "attachments.json" in zf.namelist() else {}
        missing = [meta.get("path") for meta in attachments.values() if meta.get("path") not in zf.namelist()]
        references = json.loads(zf.read("references.json").decode("utf-8")) if "references.json" in zf.namelist() else []
        markdown = [name for name in zf.namelist() if name.startswith("md/") and name.endswith(".md")]
    return {
        "ok": integrity == "ok" and not missing,
        "path": str(source),
        "integrity": integrity,
        "counts": counts,
        "attachments": len(attachments),
        "missing_assets": missing,
        "references": len(references),
        "markdown_files": len(markdown),
        "bundle": summary,
    }


def prune_bundles(directory: str | Path, *, keep: int = 5, apply: bool = False) -> dict[str, Any]:
    folder = Path(directory).expanduser()
    if not folder.is_dir():
        raise BackupError(f"backup directory not found: {folder}")
    if keep < 0:
        raise BackupError("keep must be >= 0")
    candidates = []
    for path in sorted(folder.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True):
        if len(candidates) < keep:
            candidates.append(path)
            continue
        try:
            with zipfile.ZipFile(path) as archive:
                _bundle_manifest(archive)
        except (BackupError, OSError, zipfile.BadZipFile):
            continue
        candidates.append(path)
    stale = candidates[keep:]
    stale_bytes = sum(path.stat().st_size for path in stale if path.exists())
    removed = []
    if apply:
        for path in stale:
            try:
                path.unlink()
                removed.append(str(path))
            except OSError:
                pass
    return {
        "ok": True,
        "directory": str(folder),
        "keep": keep,
        "apply": apply,
        "kept": [str(path) for path in candidates[:keep]],
        "candidates": [str(path) for path in stale],
        "removed": removed,
        "bytes": stale_bytes,
    }
