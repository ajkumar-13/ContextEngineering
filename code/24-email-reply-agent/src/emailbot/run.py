"""End-to-end runner: poll mailbox -> triage -> draft -> send-gate -> write."""
from __future__ import annotations

import os
from pathlib import Path

from .draft import draft as draft_thread
from .mailbox import get_mailbox
from .replies import index_sent_folder
from .send_gate import send_gate
from .triage import triage as triage_thread


def run_once() -> None:
    data_dir = Path(os.environ.get("EMAILBOT_DATA_DIR", "data"))
    sent_folder = data_dir / "sent"
    if sent_folder.exists():
        n = index_sent_folder(sent_folder)
        if n:
            print(f"  indexed {n} new prior replies")

    mb = get_mailbox()
    threads = mb.list_new_threads()
    if not threads:
        print("no new threads.")
        return

    for t in threads:
        tid, msgs = t["id"], t["messages"]
        print(f"\nthread {tid}: {len(msgs)} message(s)")
        triage_out = triage_thread(msgs)
        print(f"  triage: {triage_out['bucket']} ({triage_out['reason']})")
        if triage_out["bucket"] != "reply_needed":
            mb.mark_processed(tid)
            continue

        drafted = draft_thread(msgs)
        body = drafted.get("draft")
        if not body:
            print(f"  drafter returned null: {drafted.get('reason','')}")
            mb.mark_processed(tid)
            continue

        decision = send_gate(body, msgs)
        meta = {
            "thread_id": tid,
            "from": msgs[-1]["from"],
            "subject": msgs[-1].get("subject", ""),
            "needs_attention": str(drafted.get("needs_attention", False)),
            "suggested_label": drafted.get("suggested_label", ""),
            "send_gate": "ok" if decision.ok else f"BLOCK:{decision.reason}",
        }
        path = mb.write_draft(tid, body, meta)
        print(f"  draft written: {path}")
        if not decision.ok:
            print(f"  ⚠ send-gate would block: {decision.reason}")
        mb.mark_processed(tid)


if __name__ == "__main__":
    run_once()
