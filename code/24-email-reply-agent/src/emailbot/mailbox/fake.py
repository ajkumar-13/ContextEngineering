"""Disk-backed mailbox for offline development.

Layout:
  data/inbox/   *.json   each file = one thread  [{from, subject, body}, ...]
  data/drafts/  written by the agent
  data/state.json  tracks processed thread ids
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class FakeMailbox:
    def __init__(self) -> None:
        self.root = Path(os.environ.get("EMAILBOT_DATA_DIR", "data"))
        self.inbox = self.root / "inbox"
        self.drafts = self.root / "drafts"
        self.state_file = self.root / "state.json"
        self.drafts.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)

    def _state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {"processed": []}

    def _save_state(self, state: dict) -> None:
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def list_new_threads(self) -> list[dict]:
        state = self._state()
        processed = set(state["processed"])
        out: list[dict] = []
        for p in sorted(self.inbox.glob("*.json")):
            tid = p.stem
            if tid in processed:
                continue
            messages = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": tid, "messages": messages})
        return out

    def mark_processed(self, thread_id: str) -> None:
        state = self._state()
        if thread_id not in state["processed"]:
            state["processed"].append(thread_id)
        self._save_state(state)

    def write_draft(self, thread_id: str, body: str, meta: dict) -> str:
        ts = int(time.time())
        path = self.drafts / f"{ts}__{thread_id}.md"
        header = "\n".join(f"{k}: {v}" for k, v in meta.items())
        path.write_text(f"---\n{header}\n---\n\n{body}\n", encoding="utf-8")
        return str(path)
