# 24 · Email-reply agent — runnable skeleton

A complete, runnable **skeleton** of the capstone from
[Post 24](../../posts/24-capstone-email-reply-agent/index.md). Implements
the full architecture — triager sub-agent, drafter, send-gate, memory,
RAG over prior replies — against a **fake mailbox driver** so the pipeline
runs end-to-end with no cloud setup.

The Gmail driver is one file; swap it for the fake one when you wire up
real OAuth.

## Quickstart

```powershell
cd code/24-email-reply-agent
uv sync
copy .env.example .env           # set OPENAI_API_KEY, optional VOYAGE_API_KEY
uv run python -m emailbot.run
```

The script polls the fake mailbox in `data/inbox/`, runs each thread
through triager → drafter → send-gate, and writes drafts to `data/drafts/`
for review. No emails leave the machine.

## What's wired

- **Triager sub-agent** (`emailbot/triage.py`) — classifies threads into
  `reply_needed` / `info_only` / `promotional` / `automated_no_reply`.
  Cheap model, tiny prompt, no tools.
- **Drafter** (`emailbot/draft.py`) — five-block system prompt, recipient
  memory, RAG over prior replies, tool layer for calendar lookup.
- **Memory** (`emailbot/memory.py`) — three SQLite tables (episodic,
  semantic, procedural), each with provenance and timestamps.
- **RAG over prior replies** (`emailbot/replies.py`) — embeds your sent
  folder into Chroma; bookend-packed into the drafter prompt.
- **Send-gate** (`emailbot/send_gate.py`) — three deterministic checks
  (URL allow-list, no new monetary terms, business-hour times only).
- **Mailbox drivers** (`emailbot/mailbox/`) — `fake.py` reads from disk;
  `gmail.py` is a stub showing where Google's API plugs in.

## What's deliberately stubbed

- **Gmail driver** — interface defined; live implementation is a TODO with
  pointers to the Google API docs and required scopes.
- **Approval UI** — drafts are written to disk; the post describes a
  Vercel + Next.js UI on top.
- **Eval harness** — fixtures format and metric definitions live in
  `emailbot/eval.py`; running it requires real ground-truth replies.

## Layout

```
.
├── README.md
├── pyproject.toml
├── .env.example
├── data/
│   ├── inbox/                    # fake threads (.json)
│   ├── sent/                     # past replies for RAG (.txt)
│   └── drafts/                   # written by the agent
├── prompts/
│   ├── drafter_system.md
│   └── triager_system.md
├── src/emailbot/
│   ├── __init__.py
│   ├── llm.py
│   ├── memory.py
│   ├── replies.py
│   ├── triage.py
│   ├── draft.py
│   ├── send_gate.py
│   ├── run.py
│   ├── eval.py
│   └── mailbox/
│       ├── __init__.py
│       ├── base.py
│       ├── fake.py
│       └── gmail.py             # stub
└── tests/
    ├── test_send_gate.py
    └── test_triage.py
```

## License

MIT for code; CC BY 4.0 for prose. See repo root.
