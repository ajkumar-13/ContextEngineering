"""Three-table memory store: episodic, semantic, procedural.

Each row carries provenance and a timestamp; decay is a periodic job.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(os.environ.get("EMAILBOT_DATA_DIR", "data")) / "memory.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT NOT NULL,
    subject TEXT,
    summary TEXT NOT NULL,
    sent_at REAL NOT NULL,
    source TEXT
);
CREATE TABLE IF NOT EXISTS semantic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.7,
    last_confirmed_at REAL NOT NULL,
    source TEXT
);
CREATE TABLE IF NOT EXISTS procedural (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    rule TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episodic_recipient ON episodic(recipient);
CREATE INDEX IF NOT EXISTS idx_semantic_recipient ON semantic(recipient);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(_SCHEMA)
    return c


def add_episodic(recipient: str, subject: str, summary: str, source: str = "auto") -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO episodic(recipient, subject, summary, sent_at, source) VALUES (?,?,?,?,?)",
            (recipient.lower(), subject, summary, time.time(), source),
        )


def add_semantic(recipient: str, kind: str, content: str, *, confidence: float = 0.7, source: str = "auto") -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO semantic(recipient, kind, content, confidence, last_confirmed_at, source) VALUES (?,?,?,?,?,?)",
            (recipient.lower(), kind, content, confidence, time.time(), source),
        )


def recall_recipient(recipient: str, *, episodic_k: int = 3, semantic_k: int = 5) -> str:
    """Return a small text bundle to pack into the drafter prompt."""
    r = recipient.lower()
    with _conn() as c:
        ep = c.execute(
            "SELECT subject, summary, sent_at FROM episodic WHERE recipient=? ORDER BY sent_at DESC LIMIT ?",
            (r, episodic_k),
        ).fetchall()
        se = c.execute(
            "SELECT kind, content, confidence FROM semantic WHERE recipient=? ORDER BY confidence DESC, last_confirmed_at DESC LIMIT ?",
            (r, semantic_k),
        ).fetchall()
    if not ep and not se:
        return f"[memory: about {recipient}]\n- (no prior interactions on file)\n"
    lines = [f"[memory: about {recipient}]"]
    for row in se:
        lines.append(f"- {row['kind']}: {row['content']} (conf {row['confidence']:.2f})")
    if ep:
        lines.append("")
        lines.append("[memory: recent threads]")
        for row in ep:
            lines.append(f"- {row['subject']}: {row['summary']}")
    return "\n".join(lines) + "\n"
