"""Send-gate: deterministic checks that run after the human approves.

Three checks: URL allow-list, no new monetary terms, business-hour times only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

URL_RE = re.compile(r"https?://[^\s\)\]]+", re.IGNORECASE)
MONEY_RE = re.compile(r"(?:\$|USD|INR|₹|€|£)\s?\d[\d,]*(?:\.\d+)?", re.IGNORECASE)
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
BUSINESS_START_H = 9
BUSINESS_END_H = 18


@dataclass(frozen=True)
class SendDecision:
    ok: bool
    reason: str = ""

    @classmethod
    def OK(cls) -> "SendDecision":
        return cls(True)

    @classmethod
    def BLOCK(cls, reason: str) -> "SendDecision":
        return cls(False, reason)


def _urls_in(text: str) -> set[str]:
    return {u.rstrip(".,;:") for u in URL_RE.findall(text or "")}


def send_gate(draft_body: str, thread: list[dict], *, known_urls: set[str] | None = None) -> SendDecision:
    body = draft_body or ""
    thread_text = "\n".join(m.get("body", "") for m in thread)

    # 1. URL allow-list
    allowed = _urls_in(thread_text) | (known_urls or set())
    for url in _urls_in(body):
        if url not in allowed:
            return SendDecision.BLOCK(f"unknown_url:{url}")

    # 2. No new monetary terms
    if MONEY_RE.search(body) and not MONEY_RE.search(thread_text):
        return SendDecision.BLOCK("introduced_monetary_term")

    # 3. No times outside business hours
    for h_str, _ in TIME_RE.findall(body):
        h = int(h_str)
        if h < BUSINESS_START_H or h >= BUSINESS_END_H:
            return SendDecision.BLOCK(f"non_business_hour:{h:02d}")

    return SendDecision.OK()
