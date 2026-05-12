"""Mailbox drivers: fake (disk) and gmail (stub)."""
from __future__ import annotations

import os

from .base import Mailbox
from .fake import FakeMailbox


def get_mailbox() -> Mailbox:
    kind = os.environ.get("EMAILBOT_MAILBOX", "fake").lower()
    if kind == "fake":
        return FakeMailbox()
    if kind == "gmail":
        from .gmail import GmailMailbox
        return GmailMailbox()
    raise ValueError(f"unknown EMAILBOT_MAILBOX: {kind}")
