# 24 · Capstone — Email reply agent

> **TL;DR.** A complete, deployable email-reply agent that combines **everything in this series**: a five-block system prompt, RAG over the user's prior emails for tone and context, an MCP-style tool layer for Gmail (read, draft, send), per-user memory of recipients and styles, sub-agent isolation for "draft a reply" vs. "decide whether to reply", auto-compaction on long threads, an eval harness with held-out replies, and observability with cost/latency/quality dashboards. Deployed to Vercel + Railway for under $20/month for personal use. The post is the integration story — how the principles compose; the companion code is the working application.
>
> **Reading time:** ~14 minutes.
>
> **After reading this you will be able to:**
> - See how every earlier post applies in a single working system.
> - Adapt the architecture to your own production agent project.
> - Take this as a credible portfolio piece.
>
> **Companion code:** `code/24-email-reply-agent/`. Full sources, infra-as-code, deployment guide.

---

## 1. The problem

Inbox triage is a knowledge-worker tax. A draft-reply agent that actually understands your tone and context — not a generic "thank you for your email" generator — saves hours per week. It is also one of the best test-beds for context engineering because it touches every layer:

- **System prompt** — your identity, your rules, your format.
- **Tools** — read, draft, send (and a guard on send).
- **Memory** — what you have said to this recipient before, your stylistic preferences.
- **Retrieval** — your prior replies on similar topics, for tone transfer.
- **Compression** — long threads must be summarised before drafting.
- **Isolation** — "decide whether to reply at all" is a different task from "draft the reply"; a sub-agent does the first.
- **Observability** — every draft is a trace; every send is an audit row.
- **Security** — `send_email` is the most dangerous tool in the inbox.
- **Evaluation** — held-out replies as ground truth; LLM-as-judge for tone fidelity.

A capstone that hits all of these is also realistic: every box is there because *not* having it bites in production.

---

## 2. Architecture at a glance

```
┌──────────────────────────────────────────────────────────────────┐
│                       email-reply agent                           │
│                                                                  │
│  ┌─────────────┐   ┌────────────┐   ┌────────────────────────┐  │
│  │   triager   │ → │   drafter  │ → │  reviewer / send-gate  │  │
│  │ (sub-agent) │   │ (main agent)   │ (deterministic + user) │  │
│  └─────────────┘   └────────────┘   └────────────────────────┘  │
│        ↑                  ↑                                      │
│        │                  │                                      │
│   Gmail tools       RAG over my replies                          │
│   memory store      compression on long threads                  │
└──────────────────────────────────────────────────────────────────┘
            │                                      │
            ▼                                      ▼
   ┌────────────────┐                    ┌────────────────────┐
   │  Vercel (web)  │                    │  Railway (worker)  │
   │  approve UI    │                    │  scheduled poll    │
   └────────────────┘                    └────────────────────┘
```

A scheduled worker on Railway polls Gmail every 10 minutes (or listens to push notifications). For each new thread, it runs the **triager** sub-agent: should this even get a reply? If yes, it runs the **drafter** main agent, which uses Gmail tools, RAG over your prior replies, and your memory store. The output is a draft; a deterministic guard checks for hard rules; the result lands in a Vercel-hosted approval UI; you click send (or edit-and-send) from your phone.

Three properties to notice:

- **Send is never automatic.** The agent drafts; the human ships. This is Post 18, §3, Defence 1 applied where it matters most.
- **The drafter never sees the *whole* inbox.** Only the current thread, plus selectively retrieved prior replies. The selection is the engineering.
- **Approval generates labels.** Each approve/reject/edit is a fixture for the eval harness — the system improves itself from real feedback.

---

## 3. The system prompt

```markdown
# Identity
You are the email-reply assistant for Dr Shrirat Panat, an educator
and engineer at Vizuara. You draft replies in his voice for his
review. You never send.

# Rules
- Match the tone and length of his prior replies on similar threads.
- For unfamiliar senders, default to a polite, brief, professional tone.
- If the email is promotional, automated, or otherwise not worth a
  reply, return { "draft": null, "reason": "..." }.
- Never include URLs, attachments, or commitments not present in the
  thread or in his prior replies.
- Refer to his calendar only via the `check_availability` tool; do
  not invent times.
- Never send. Always return a draft for human review.

# Format
- Output JSON: { "draft": "<body text or null>", "reason": "<why>",
  "needs_attention": <bool>, "suggested_label": "<string>" }.
- The draft uses the same greeting and sign-off pattern as the
  retrieved prior replies.
- No markdown in the draft body — emails are plain text.

# Knowledge
- Vizuara is an AI/ML education company headquartered in Pune.
- Standard meeting slot is 30 minutes, 9:30–17:30 IST, weekdays.
- Default sign-off: "Best, Shrirat".

# Tools
- `read_thread(thread_id)` — fetch the full thread.
- `retrieve_prior_replies(query, k=5)` — RAG over previous replies.
- `recall_recipient(email)` — pull memory cells for this contact.
- `check_availability(window_days=7)` — calendar lookup.
```

The five blocks (Post 12, §2). The rules block bans the failure modes the author has actually hit ("never invent meeting times", "never include URLs not in the thread"). The format block enforces a JSON contract that the next stage parses. The tools block lists *only* the tools the drafter needs; the triager has its own, separate tool catalog.

---

## 4. Memory — episodic, semantic, procedural

Three tables, the taxonomy from Post 14, §1.

- **Episodic.** Each past email exchange becomes one row: `{subject, recipient, summary, sent_at, my_response_id}`. Used for "what did we discuss with this person last time".
- **Semantic.** Per-recipient preferences and facts: `{recipient, kind, content, confidence, last_confirmed_at}`. Examples: "uses formal English", "is on the engineering team at X", "prefers calls over emails".
- **Procedural.** Global rules in `prompts/rules.md`, plus per-relationship rules ("with my advisor: always use 'Dr.'", "with my co-founder: never mark messages as urgent unless they really are").

The drafter's memory layer (Post 02, §4) is assembled per-call by `recall_recipient(email)`, which queries all three tables for the current sender and returns a small bundle:

```
[memory: about this recipient]
- Anika Iyer, COO at PartnerCo. (verified from billing system)
- Prefers concise replies; usually under 80 words. (last 7 exchanges)
- We are in mid-negotiation for a partnership; expect business tone.

[memory: rules for this thread]
- Anika has been waiting 3 days for a reply on the partnership terms.
  Prioritise responsiveness.
```

Each cell has provenance and a timestamp (Post 07, §2). Decay is a nightly job that lowers confidence on cells not confirmed in 90 days.

---

## 5. Retrieval — RAG over my prior replies

The corpus is *every email I have sent in the last 12 months*. Ingested with the pipeline from Post 22 (chunk by message; contextual headers; hybrid retrieval; cross-encoder rerank). Two refinements specific to this use case:

- **Chunks are full messages**, not paragraphs. A reply is the unit of style transfer.
- **Metadata includes the recipient** for filtered retrieval. *"Past replies to Anika"* is a cheap, high-precision filter.
- **The retrieval query is the *current thread's last message + a tone prompt*.* Not just the sender's words; the embedding match needs to find replies *I* wrote in similar situations.

A typical retrieval pass returns 5 prior replies; bookend layout (Post 08, §5) puts the most relevant first and the most stylistically representative last.

The drafter sees:

```
[prior replies, for tone reference]
[reply to Anika, 2025-09-12, partnership topic] Hi Anika, ...
[reply to a different partner, 2025-08-03, scheduling] ...
[reply to Anika, 2025-07-29, intro] ...
```

The combination — recipient memory + tone-matched prior replies + the current thread — gives the model the smallest possible context that contains everything it needs to produce a reply that sounds like the user.

---

## 6. Compression — long threads

Long email threads (5+ messages) burn budget fast. The compression policy (Post 10, §7):

- **Soft trigger at 80 %** of the thread budget: tool-result clearing and priority pruning. Earlier quoted-reply blocks (the `>` chains) are clipped; structural metadata stays.
- **Hard trigger at 95 %**: a sub-agent summarises the older portion of the thread into a 200-token brief; the latest 2–3 messages stay verbatim.

The summary uses the structured prompt from Post 10, §3 — preserve decisions, open questions, stated facts, in priority order. The drafter receives the summary plus the recent messages and behaves as if it had the whole thread.

---

## 7. The triager sub-agent

The triager runs first on every thread. Its job: classify the thread into one of four buckets — `reply_needed`, `info_only`, `promotional`, `automated_no_reply`. The output is a small JSON object the orchestrator routes on.

Why a sub-agent?

- **Different tools.** The triager only needs to *read*; it does not need draft or send tools. Smaller catalog → smaller prompt → faster, cheaper.
- **Different context.** The triager does not need prior replies or recipient memory. It just needs the thread.
- **Different model.** A small fast model is sufficient; the drafter uses the bigger, slower one.

Cost arithmetic (Post 11, §8): the triager costs ~$0.001 per thread; it filters out 60–70 % of threads from ever reaching the drafter (~$0.05 per draft). Net savings: roughly 60 % of the per-day cost of running the system.

---

## 8. The send-gate

Even after the human approves, a deterministic guard runs before the actual `send_email` call:

```python
def send_gate(draft: dict, thread: list[dict]) -> SendDecision:
    body = draft["body"]
    # 1. URL allow-list: no URLs that did not appear in the thread or
    #    in a known set of personal/company URLs
    for url in extract_urls(body):
        if url not in known_urls(thread):
            return SendDecision.BLOCK("unknown_url:" + url)
    # 2. No new monetary commitments
    if mentions_money(body) and not any(mentions_money(m["body"]) for m in thread):
        return SendDecision.BLOCK("introduced_monetary_term")
    # 3. No times outside business hours
    for t in extract_times(body):
        if not in_business_hours(t):
            return SendDecision.BLOCK("non_business_hour:" + str(t))
    return SendDecision.OK
```

This is Post 18, §3, Defence 1 *in code* — the model proposed; the application enforces. Three concrete checks; the agent can produce drafts that fail any of them, and the system does the right thing without depending on the prompt to forbid them.

---

## 9. Observability and eval

**Trace per session.** The whole pipeline — triager call, drafter call (with retrieval + memory + tools), send-gate decision, user action (approve / edit / reject) — emits one trace with nested spans (Post 17, §3). The trace is the primary debugging artefact.

**Four headline metrics** on the dashboard (Post 17, §4): cost per draft, p95 latency, **approval rate** (the user's accept/edit/reject as the quality proxy), error rate by kind.

**Eval harness** (Post 16, §4) runs nightly on a held-out set of historical threads with the user's actual replies as ground truth. Three metrics:

- **Tone fidelity** — an LLM-judge prompt that scores how close the draft sounds to the user's own writing on a 1–5 scale.
- **Factual faithfulness** — claims in the draft are supported by the thread or by retrieved memory.
- **Decision accuracy** — the triager's classification matches the user's revealed preference (did the human reply? was it promotional?).

A regression on any of these blocks the deploy. The harness gets stronger every week as approve/reject data accumulates.

---

## 10. Deployment

The whole system fits a small modern stack.

- **Vercel** for the approval UI (Next.js). Serverless functions for the OAuth callback and the approve endpoint.
- **Railway** for the worker (Python). Cron schedule polls Gmail every 10 minutes; long-running drafts run as one-off workers.
- **Postgres** (Railway's managed instance) for memory, audit log, eval fixtures, and the trace store.
- **Chroma** (or pgvector) for the email-corpus index.
- **Anthropic API** for the drafter; a smaller model (or a Voyage / Cohere classifier) for the triager.

Personal-use cost: roughly $5/month for Railway, $0 for Vercel hobby tier, $5–15/month for the LLM bill at typical inbox volume. The whole thing is under $20/month for one person; a team variant scales linearly with users.

The full deployment guide — environment variables, OAuth setup, Gmail scopes, Vercel config, Railway services, the cron schedule, the secret manager — lives in `code/24-email-reply-agent/README.md`.

---

## 11. The lesson the capstone teaches

The capstone is not impressive because it has more code than the other builds. It is impressive because every choice in it has a *reason*, and every reason traces to one of the earlier posts. The system prompt has five blocks because [Post 12](../12-system-prompt-as-software/index.md) said it should. The retrieval is hybrid + reranked because [Post 08](../08-select-strategies/index.md) said so. The triager is a sub-agent because [Post 11](../11-isolate-strategies/index.md) said so. The send-gate is in code because [Post 18](../18-security/index.md) said it had to be.

This is the shape of a serious LLM system. None of it is heroic; all of it is *deliberate*. A team that can build this can build the next one.

---

## 12. Where to go next

A short list of directions worth exploring once the capstone is running.

- **Active learning.** Every user edit on a draft becomes a training signal. Periodically fine-tune a small model on the (draft, edited-draft) pairs for tone transfer; the LLM-judge stays as backstop.
- **Cross-channel.** The same architecture works for Slack, Discord, LinkedIn messages. Swap Gmail tools for the channel's API; everything else stays.
- **Multi-user.** A team variant where the agent learns each user's voice; the memory store gets a `user_id` column and a tenant boundary.
- **Voice notes.** A voice-to-draft pipeline using Whisper + the same drafter chain; useful for replying on the move.
- **Scheduling agent.** A second agent specialised for calendar logistics, called via the tools layer when a thread becomes a scheduling thread.

Each of these is a small step; the foundation supports them all without re-architecting.

---

## 13. Closing — what the series tried to do

This series began with the claim that *prompt engineering* was the right name for 2022–2023 and *context engineering* is the right name for the era we are now in. Twenty-four posts later, the case the series tried to make is concrete:

- The model receives a stack of layers; each layer is engineered separately ([Post 02](../02-six-layers-of-context/index.md)).
- The model reads that stack with measurable, predictable biases ([Post 03](../03-how-llms-read-context/index.md)).
- Every token costs money and time and attention; the engineering is making each one count ([Post 04](../04-tokens-windows-budgets/index.md)).
- Failures have names and shapes; they are not mysterious ([Post 05](../05-context-failure-modes/index.md)).
- Four operations cover almost every technique — Write, Select, Compress, Isolate ([Posts 06–11](../06-write-select-compress-isolate/index.md)).
- Each layer is its own engineering discipline ([Posts 12–15](../12-system-prompt-as-software/index.md)).
- Production demands eval, observability, and security as first-class concerns ([Posts 16–19](../16-evaluation/index.md)).
- The modern workflow puts these disciplines in the editor and on the server ([Posts 20–21](../20-modern-agentic-workflow/index.md)).
- The builds (Posts 22–24) are how the principles become muscle memory.

The hope: that someone reading this series end-to-end is now equipped to ship LLM systems that improve over time instead of decaying — and to teach the next person the same.

Thank you for reading.

— Vizuara · Dr Shrirat Panat

---

## Common pitfalls

- **Auto-send.** The agent drafts; the human ships. Skipping the gate is the one mistake that ends the project on day one.
- **Drafting without memory.** The replies are technically correct and emotionally generic. The memory layer is the difference.
- **Drafting without prior-reply RAG.** The drafts sound like an LLM, not like the user.
- **Skipping the triager.** The drafter runs on every promotional email; cost and quality both suffer.
- **No approval-data feedback loop.** The system never learns from edits.
- **No send-gate.** The first time the model hallucinates a URL, you find out by sending it.

---

## Further reading

- See the 23 prior posts. Every section above traces to one of them.
- Google, *"Gmail API"* docs (latest).
- Vercel, *"Next.js + serverless functions"* docs.
- Railway, *"Workers and cron"* docs.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **Re-read [Post 01](../01-why-context-engineering/index.md)** with the capstone in mind.
- **The [GLOSSARY](../../GLOSSARY.md)** — every term you have learned in one place.
- **The [CHEATSHEET](../../CHEATSHEET.md)** — the printable single-page summary.
- **Build something of your own**, and tell us about it.
