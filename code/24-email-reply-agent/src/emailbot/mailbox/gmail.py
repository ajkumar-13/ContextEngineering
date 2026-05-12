"""Gmail mailbox driver — STUB.

To implement live:
  1. Enable the Gmail API in a Google Cloud project.
  2. Create OAuth 2.0 credentials (Desktop app); download client_secret.json.
  3. Request scopes:
       https://www.googleapis.com/auth/gmail.readonly
       https://www.googleapis.com/auth/gmail.compose
     (Do NOT request gmail.send for the agent path; the human ships.)
  4. Persist the refresh token securely (Secret Manager / OS keychain).
  5. Implement the three methods below using google-api-python-client:
       - users().messages().list / .get for threads
       - users().drafts().create for write_draft
       - a local ledger for processed thread ids

See https://developers.google.com/gmail/api/quickstart/python for the
canonical quickstart.
"""
from __future__ import annotations


class GmailMailbox:
    def __init__(self) -> None:
        raise NotImplementedError(
            "Gmail driver not implemented in the starter. See module docstring "
            "for the steps. Use EMAILBOT_MAILBOX=fake for offline development."
        )

    def list_new_threads(self) -> list[dict]:
        raise NotImplementedError

    def mark_processed(self, thread_id: str) -> None:
        raise NotImplementedError

    def write_draft(self, thread_id: str, body: str, meta: dict) -> str:
        raise NotImplementedError
