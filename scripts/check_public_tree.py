#!/usr/bin/env python3
"""Mandatory sanitization check for every push.

Scans tracked files (or the working tree before the first commit) for:

- required public files and bilingual pairs;
- absolute user-home paths (macOS, Linux, Windows);
- API keys/tokens and generic credential assignments;
- private keys, emails, and private network addresses;
- local databases, keys, env files, and oversized assets.

Exit code 0 means the public tree is clean; any finding fails the push.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "NOTICE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "VERSION",
    "pyproject.toml",
    "CHANGELOG.md",
    "requirements.txt",
    "requirements-dev.txt",
    ".gitattributes",
    ".gitignore",
    ".githooks/pre-push",
    "AGENTS.md",
    "docs/en/quickstart.md",
    "docs/zh-CN/quickstart.md",
    "examples/hello-project/README.md",
    "examples/two-ide-handoff/README.md",
    "tests/test_public_tree.py",
    ".github/workflows/ci.yml",
]

TEXT_SUFFIXES = {
    ".md", ".txt", ".yml", ".yaml", ".json", ".toml",
    ".py", ".sh", ".ps1", ".cmd", ".bat", ".gitignore", ".gitattributes",
    ".cfg", ".ini",
}

FORBIDDEN_NAMES = {
    ".env", ".env.local", "config.yaml", "config.local.yaml",
    "cookies.txt", "id_rsa", "id_ed25519",
}
FORBIDDEN_SUFFIXES = {
    ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3",
    ".key", ".pem", ".p12", ".log", ".bak",
}

# Build sensitive patterns without embedding a ready-to-use credential.
PATTERNS = [
    ("user-home path", re.compile(r"/Users/[A-Za-z0-9._-]+/")),
    ("home path", re.compile(r"/home/[A-Za-z0-9._-]+/")),
    ("macOS private path", re.compile(r"/private/(?:var|tmp)/")),
    ("macOS var-folder path", re.compile(r"/var/folders/")),
    ("windows user path", re.compile(r"[A-Za-z]:\\Users\\")),
    ("windows UNC user path", re.compile(r"\\\\Users\\")),
    ("private network address", re.compile(
        r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.")),
    ("openai-like key", re.compile(r"\b[s]k-[A-Za-z0-9_-]{20,}")),
    ("anthropic-like key", re.compile(r"\b[s]k-ant-[A-Za-z0-9_-]{20,}")),
    ("github classic token", re.compile(r"\bgh[p]_[A-Za-z0-9]{20,}")),
    ("github fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("stripe live key", re.compile(r"\bsk_live_[A-Za-z0-9]{10,}")),
    ("private key block", re.compile(r"BEGIN [A-Z ]*PRIV" + "ATE KEY")),
    ("credential assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\s*[:=]\s*[\"'][^\"']{8,}[\"']")),
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}
MAX_BYTES = 1_000_000
CHECKER = "scripts/check_public_tree.py"


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
        ).stdout
        names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
        if names:
            return [ROOT / n for n in names]
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in ROOT.rglob("*") if p.is_file()]


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def main() -> int:
    problems = 0

    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing {rel}")
            problems += 1

    readme_en = ROOT / "README.md"
    readme_zh = ROOT / "README.zh-CN.md"
    if readme_en.is_file() and "README.zh-CN.md" not in readme_en.read_text(encoding="utf-8"):
        fail("README.md does not link README.zh-CN.md")
        problems += 1
    if readme_zh.is_file() and "README.md" not in readme_zh.read_text(encoding="utf-8"):
        fail("README.zh-CN.md does not link README.md")
        problems += 1

    en_dir = ROOT / "docs" / "en"
    zh_dir = ROOT / "docs" / "zh-CN"
    if en_dir.is_dir() and zh_dir.is_dir():
        en = {p.name for p in en_dir.glob("*.md")}
        zh = {p.name for p in zh_dir.glob("*.md")}
        for name in sorted(en ^ zh):
            fail(f"docs pair mismatch: {name}")
            problems += 1
    else:
        fail("docs/en or docs/zh-CN missing")
        problems += 1

    for path in tracked_files():
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            fail(f"forbidden file: {rel}")
            problems += 1
            continue
        size = path.stat().st_size
        if size > MAX_BYTES:
            fail(f"large file {size} bytes: {rel}")
            problems += 1
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            ".gitignore", ".gitattributes"
        }:
            continue
        if rel == CHECKER:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                fail(f"{label} in {rel}:{line}")
                problems += 1

    if problems:
        print(f"\n{problems} problem(s); push blocked")
        return 1
    print("PASS: public tree is sanitized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
