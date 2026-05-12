"""Mailbox driver protocol. Two implementations live in this folder."""
from __future__ import annotations

from typing import Protocol


class Mailbox(Protocol):
    def list_new_threads(self) -> list[dict]: ...
    def mark_processed(self, thread_id: str) -> None: ...
    def write_draft(self, thread_id: str, body: str, meta: dict) -> str: ...
