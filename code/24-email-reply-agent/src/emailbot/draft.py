"""Drafter: assembles memory + RAG + thread, calls the model, returns JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .llm import chat
from .memory import recall_recipient
from .replies import pack_prior_replies, retrieve_prior_replies

SYSTEM = (Path(__file__).resolve().parents[2] / "prompts" / "drafter_system.md").read_text(encoding="utf-8")


def _render_thread(thread: list[dict]) -> str:
    return "\n\n".join(
        f"--- message {i+1} ---\nFrom: {m['from']}\nSubject: {m.get('subject','')}\n\n{m['body']}"
        for i, m in enumerate(thread)
    )


def draft(thread: list[dict]) -> dict:
    sender = thread[-1]["from"]
    last_msg = thread[-1]["body"]
    memory_block = recall_recipient(sender)
    prior = retrieve_prior_replies(last_msg, recipient=sender, k=5)
    prior_block = pack_prior_replies(prior)
    thread_block = _render_thread(thread)
    user = (
        f"{memory_block}\n{prior_block}\n[current thread]\n{thread_block}\n\n"
        f"Draft a reply for review. Return JSON only."
    )
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
    raw = chat(
        msgs,
        model=os.environ.get("EMAILBOT_DRAFT_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
    )
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return {"draft": None, "reason": "drafter_json_parse_error", "needs_attention": True, "suggested_label": ""}
    return {
        "draft": out.get("draft"),
        "reason": out.get("reason", ""),
        "needs_attention": bool(out.get("needs_attention", False)),
        "suggested_label": out.get("suggested_label", ""),
    }
