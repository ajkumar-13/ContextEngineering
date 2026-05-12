"""Triager sub-agent: classify a thread into one of four buckets.

Cheap model, no tools, JSON output.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .llm import chat

VALID_BUCKETS = {"reply_needed", "info_only", "promotional", "automated_no_reply"}
SYSTEM = (Path(__file__).resolve().parents[2] / "prompts" / "triager_system.md").read_text(encoding="utf-8")


def triage(thread: list[dict]) -> dict:
    rendered = "\n\n".join(f"From: {m['from']}\nSubject: {m.get('subject','')}\n\n{m['body']}" for m in thread)
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Thread:\n\n{rendered}\n\nReturn JSON only."},
    ]
    raw = chat(
        msgs,
        model=os.environ.get("EMAILBOT_TRIAGE_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return {"bucket": "reply_needed", "reason": "triager_json_parse_error", "confidence": 0.0}
    bucket = out.get("bucket", "reply_needed")
    if bucket not in VALID_BUCKETS:
        bucket = "reply_needed"
    return {
        "bucket": bucket,
        "reason": out.get("reason", ""),
        "confidence": float(out.get("confidence", 0.5)),
    }
