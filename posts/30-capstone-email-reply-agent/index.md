# 30 - Capstone: email reply agent

> **TL;DR.** An email reply agent touches every part of this series at once: a triager sub-agent decides whether a thread needs a reply, a drafter reads a five-block system prompt, recipient memory, bookend-packed prior replies and the thread, and a send gate in code checks every draft before it can leave. The companion runs that pipeline against a fake mailbox and its offline tests prove the gate's checks; Gmail, the approval interface, compression, tracing and the evaluation gate are live steps described from their documentation. Nine drafts through the gate show what a deterministic check buys and what it misses, which is why a person stays in the loop.
>
> **Prerequisites:** [Post 14](../14-system-prompt-as-software/index.md), [Post 16](../16-memory-systems/index.md), [Post 20](../20-evaluation/index.md), [Post 22](../22-observability/index.md), [Post 23](../23-security/index.md), [Post 28](../28-build-rag-chatbot/index.md), [Post 29](../29-build-mcp-server/index.md).
> **Safe to skip?** Skip it if an agent of one's own already traces every component to the layer it fills, gates every outbound action in code, and separates what its offline tests prove from what only a live deployment shows.
>
> **After reading, you will be able to:**
>
> - Trace each part of the email reply agent to the layer it fills, the operation it performs and the earlier post that teaches it.
> - Assemble the drafter's request in layer order from the five-block system prompt, recipient memory, bookend-packed prior replies and the thread.
> - Justify the triager as an isolated sub-agent and compute its saving for a stated inbox mix and per-call costs.
> - Predict which drafts the send gate's three checks block or let through, and explain why the gate runs in code after a human approves.
> - Separate what the companion's offline tests prove from what needs keys and live services when presenting or adapting the build.

![A mailbox feeds a triager; threads it marks reply_needed go to a drafter that reads the system prompt, a memory store and an index of prior replies, and writes a draft. The draft goes to human review, then a send gate in code, then send; a blocked draft goes back. The Gmail driver, review and send are dashed: live steps the companion does not include.](diagrams/00-hero-capstone-email-reply-agent.svg)

*The model only ever writes a draft; what leaves the mailbox passes a person and a check in code.*

---

## 1. The question: how does one agent use every earlier post?

A drafting agent that knows the user's tone and history, not a generic "thank you for your email" generator, saves real time on a full inbox. It is also a test bed for context engineering, because it touches all six layers of [post 02](../02-six-layers-of-context/index.md): layer 01, the system prompt, holds the user's identity and inbox rules; layer 02, tools and MCP (Model Context Protocol) descriptions, the mailbox actions; layer 03, memory and state, what the user knows about this sender; layer 04, retrieved chunks, the user's earlier replies; layer 05, conversation history, the email thread itself; and layer 06, the user instruction, the request to draft. It uses isolate for the decision whether to reply at all, and it needs every production discipline: traces, held-out evaluation, and a guard on `send`, the most dangerous action in the inbox.

The question is how these compose into one agent that can be run, tested and deployed. The companion, [`code/30-email-reply-agent`](../../code/30-email-reply-agent/), is a runnable skeleton of the triager, drafter, memory, retrieval and send gate against a fake mailbox; this post says, part by part, what it does, what its tests prove, and what a deployment adds.

---

## 2. Architecture at a glance

The figure at the top draws the pipeline. A mailbox driver lists new threads: `FakeMailbox` reads JSON (JavaScript Object Notation) files from `data/inbox/`, and `GmailMailbox` is a stub that raises `NotImplementedError` and lists the steps a live driver needs. The **triager** puts each thread in one of four buckets; only a `reply_needed` thread goes to the **drafter**, which assembles memory, prior replies and the thread into one request and asks for the draft as JSON. The **send gate** checks the draft, and the runner writes it with the verdict to `data/drafts/`; no email leaves the machine.

A deployment adds two steps: a person approves, edits or rejects each draft in an approval interface, and only an approved draft reaches the send path, where the gate runs again on the final text. Three properties matter more than any one component:

- **Sending is never automatic.** This is defence D1 of [post 23](../23-security/index.md), section 5, where an action is hardest to undo: the model proposes, the application decides.
- **The drafter never sees the whole inbox**: only the thread, a few lines of memory about the sender and a handful of earlier replies to them (section 6).
- **Every decision is a label.** Approved, edited and rejected drafts become the held-out cases of the evaluation set (section 10).

---

## 3. The system prompt: five blocks

The drafter's system prompt, `prompts/drafter_system.md`, has the five blocks of [post 14](../14-system-prompt-as-software/index.md), section 2: identity, rules, format, knowledge and tool-use guidance. Its first two:

```markdown
# Identity
You are the email-reply assistant for {{USER_NAME}}, an educator and engineer
who writes the Context Engineering series. You draft replies in their voice for their review. You never send.

# Rules
- Match the tone and length of the prior replies provided below on similar threads.
- For unfamiliar senders, default to a polite, brief, professional tone.
- If the email is promotional, automated, or otherwise not worth a reply,
  return { "draft": null, "reason": "..." }.
- Never include URLs, attachments, or commitments not present in the
  thread or in prior replies.
- Refer to the calendar only if explicitly told a slot; do not invent times.
- Never send. Always return a draft for human review.
```

The rules ban the failures that bite in an inbox: an invented meeting time, a link (URL, uniform resource locator) or a commitment found nowhere in the thread. The format block asks for JSON with four fields (`draft`, `reason`, `needs_attention`, `suggested_label`) and the sign-off "Best, Ajay" by default; the knowledge block gives 30-minute slots from 09:00 to 18:00 India Standard Time (IST) on weekdays; the `# Tools` block says this skeleton has none; a deployed drafter lists one line per tool there, and the Gmail tools' schemas go in layer 02 ([post 15](../15-tools-and-mcp/index.md); the MCP server build, `ctx-029`, shows a server of such tools).

`draft.py` fills `{{USER_NAME}}` from `EMAILBOT_USER_NAME` (default "Ajay Kumar") as it loads the file. The knowledge block's hours match the gate's defaults (section 9), but one rule written in two places drifts unless one copy is generated from the other.

---

## 4. Memory: three kinds of knowledge about a sender

[Post 16](../16-memory-systems/index.md) gives an agent three kinds of memory, and `memory.py` keeps them in three SQLite tables:

- **Episodic**: one row per past exchange (`recipient`, `subject`, `summary`, `sent_at`, `source`): what the user discussed with this person last time.
- **Semantic**: facts and preferences about a sender (`recipient`, `kind`, a free label such as `role` or `style`, `content`, `confidence`, `last_confirmed_at`, `source`).
- **Procedural**: rules (`scope`, `rule`, `created_at`) for learned per-sender how-tos such as "send this client's invoices as CSV".

Against the row of [post 16](../16-memory-systems/index.md), section 3 ([post 08](../08-write-strategies/index.md)'s nine fields plus `trigger`), the tables are a start, not the finished store: a procedural row has neither `source` nor `trigger`, no row has `last_accessed_at` or `expires_at`, and the procedural table is created but never written or read. The docstring promises decay as "a periodic job" that does not exist; [post 16](../16-memory-systems/index.md), section 8, decays confidence on read instead.

`recall_recipient(email)` is the read path: by default the five highest-confidence semantic facts and the three most recent episodes about the sender, as a text block for layer 03. The companion's runner writes no rows, so on its sample inbox the block always says "(no prior interactions on file)"; the snippet of section 6 writes three illustrative rows through the companion's own `add_semantic` and `add_episodic` and shows the block that comes back. Each line carries a confidence but not its source or date, which [post 16](../16-memory-systems/index.md), section 9, prints so that a confirmed fact can be told from a guess. A fact learned from an email is external text, and D4 of [post 23](../23-security/index.md) forbids it to return as a rule.

---

## 5. Retrieval over the user's prior replies

The corpus is the user's sent folder. `replies.py` embeds each sent reply whole, since a reply is the unit of style transfer, into a Chroma collection with the recipient and subject as metadata. At draft time the query is the thread's last message, the search is filtered to replies sent to the same address, and five are requested. The recipient filter is the cheapest precision there is.

The hits are packed in the bookend layout of [post 09](../09-select-strategies/index.md), section 5, a select decision: best first, second-best last, the rest between, where models use context most reliably. The core of `pack_prior_replies` in `replies.py`:

```python
    if len(hits) > 1:
        ordered = [hits[0]] + hits[2:] + [hits[1]]
    else:
        ordered = hits
```

Five replies ranked r1 to r5 are packed as `r1 r3 r4 r5 r2` (the snippet prints it); two hits, as for thread t-001, keep their rank order.

The ranking is only as good as the embedding. With `VOYAGE_API_KEY` set, `replies.py` embeds with Voyage's `voyage-3-lite`; without it, it falls back to a hashed bag of words (each word counted in one of 64 buckets by its SHA-256 hash), the same on every run but blind to meaning, so offline the recipient filter does the real work. The snippet ranks with this fallback and Chroma's default squared L2 distance. A deployment would add what [post 11](../11-rag-in-depth/index.md) and [post 17](../17-advanced-retrieval/index.md) describe and the RAG (retrieval-augmented generation) build of `ctx-028` implements: contextual headers ([post 11](../11-rag-in-depth/index.md), section 2), hybrid keyword and vector search, and reranking.

---

## 6. What the drafter sees

`draft.py` sends two messages: the system prompt, and everything else as one user message.

```python
    user = (
        f"{memory_block}\n{prior_block}\n[current thread]\n{thread_block}\n\n"
        f"Draft a reply for review. Return JSON only."
    )
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
```

The order is the layer order. The system message is layer 01; there is no layer 02, since the skeleton's drafter has no tools; memory is layer 03 and the packed replies layer 04, the per-turn injection; the thread plays layer 05, conversation history, because it is the conversation the reply continues, it grows, and it is what compression trims (section 7); the closing request is layer 06, last. `uv run python posts/30-capstone-email-reply-agent/snippets/drafter_request.py` assembles the request for thread t-001 with the companion's own functions and counts tokens with tiktoken's `o200k_base` encoding (the one for `gpt-4o-mini`, the companion's default model):

```text
user message of the drafter call for thread t-001, outline:
  [memory: about anika@partnerco.io]
  - role: COO at PartnerCo (conf 0.90)
  - style: prefers short replies (conf 0.70)
  [memory: recent threads]
  - Partnership terms: confirmed 70/30 for year one; offered a Thursday call
  [prior replies, for tone reference]
  --- to anika@partnerco.io re: partnership terms ---
      ... 5 line(s)
  --- to anika@partnerco.io re: intro ---
      ... 5 line(s)
  [current thread]
  --- message 1 ---
      ... 6 line(s)
  Draft a reply for review. Return JSON only.
tokens by layer, o200k_base:
  01 System prompt                  313
  02 Tools and MCP descriptions       0
  03 Memory and state                62
  04 Retrieved chunks               144
  05 Conversation history            72
  06 User instruction                10
  sum                               601   (system message 313, user message 289)
```

The figure below draws the six counts. More than half of the 601 tokens is the system prompt; memory, two earlier replies and the thread are under 300 (counted apart they sum to 288 against the user message's 289, since a token can span a join). What grows with the inbox is the index, not the request.

![Six horizontal bars of tokens by layer for the drafter's request on thread t-001: 01 System prompt 313, 02 Tools and MCP descriptions 0, 03 Memory and state 62, 04 Retrieved chunks 144, 05 Conversation history 72, 06 User instruction 10, in the role colours of their lifetime classes.](diagrams/02-drafter-request.svg)

*A reply is drafted from a few hundred selected tokens, not from the mailbox.*

---

## 7. Compression of long threads

Thread t-001 is one message; a real thread can run to dozens, each quoting the one before. The companion does not compress. A deployed drafter applies the two triggers of [post 12](../12-compress-strategies/index.md), section 9, whose 80 and 95 percent are illustrative defaults, measured against a budget for the thread:

- **At 80 percent, the soft trigger**: priority pruning ([post 12](../12-compress-strategies/index.md), section 5), with no model call. The quoted copies of earlier messages (the `>` chains mail clients append) go first, because those messages are already in the thread; signatures and disclaimers next.
- **At 95 percent, the hard trigger**: summarisation ([post 12](../12-compress-strategies/index.md), section 3). A separate call condenses the older messages into a brief that keeps decisions, open questions and stated facts, in that order; the latest two or three messages stay verbatim.

The summary reads all it replaces, so it runs on the trigger only.

---

## 8. The triager sub-agent

The triager runs first and classifies each thread as `reply_needed`, `info_only`, `promotional` or `automated_no_reply`. Its prompt, `prompts/triager_system.md`, has identity, rules and format blocks and says to choose `reply_needed` when torn between it and `info_only`. It uses JSON mode (`response_format={"type": "json_object"}`), which, as [post 21](../21-structured-output-guardrails/index.md) says, guarantees valid JSON and not the fields, so `triage.py` checks them:

```python
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return {"bucket": "reply_needed", "reason": "triager_json_parse_error", "confidence": 0.0}
    bucket = out.get("bucket", "reply_needed")
    if bucket not in VALID_BUCKETS:
        bucket = "reply_needed"
```

Every failure falls back to `reply_needed`: a wasted draft costs cents, a missed reply costs a relationship. This is isolation as [post 13](../13-isolate-strategies/index.md) recommends it (sections 3 and 5), a sub-task with a clean contract: the thread in, a small JSON object out. The triager needs no tools, so its window has no layer 02; it needs no memory or prior replies; and it can run on a cheaper model. The companion sets both models through `EMAILBOT_TRIAGE_MODEL` and `EMAILBOT_DRAFT_MODEL`, both defaulting to `gpt-4o-mini` through OpenAI's Chat Completions API (application programming interface), so choosing a smaller triage model is a configuration change.

What the split saves is arithmetic in the manner of [post 13](../13-isolate-strategies/index.md), section 8. With illustrative costs of a tenth of a cent per triage call and five cents per draft, and an illustrative inbox of 90 threads of which 30 need a reply, `snippets/triage_saving.py` prints:

```text
90 threads, 30 need a reply; triage 0.1 c, draft 5.0 c a call
drafter on every thread:   90 x 5.0 = 450.0 cents
triager first:             90 x 0.1 + 30 x 5.0 = 159.0 cents
saving: 291.0 cents, 64.7% of the bill
the triager pays for itself once more than 2% of threads are filtered
```

The last line is the general rule: the triager costs $c_t$ on every thread and saves $c_d$ on every thread it filters, so it pays once the filtered share exceeds $c_t / c_d$, here $0.1 / 5 = 2$ percent. The dollars depend on the prices and the inbox; the break-even depends only on the ratio.

---

## 9. The send gate

A rule in a prompt is followed most of the time, so the companion enforces three rules in code, `send_gate.py`:

```python
def send_gate(draft_body: str, thread: list[dict], *, known_urls: set[str] | None = None) -> SendDecision:
    body = draft_body or ""
    thread_text = "\n".join(m.get("body", "") for m in thread)

    # 1. URL allow-list: only the operator's links; a link quoted from the thread is not trusted
    allowed = {u.rstrip("/") for u in (known_urls if known_urls is not None else known_urls_from_env())}
    for url in _urls_in(body):
        if url.rstrip("/") not in allowed:
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
```

This is D1 and D2 of [post 23](../23-security/index.md), section 5, in code: the draft is a proposal, and the application decides whether it may leave. It runs after the person approves because a reviewer on a phone approves a draft that still carries an invented link, and the gate does not tire. The companion has no send path, so `run.py` runs the gate as each draft is written and records `send_gate: ok` or `BLOCK:<reason>` in the draft's header; a deployment runs it again on the approved text, just before sending.

Three regular expressions block exactly what they match. `uv run python posts/30-capstone-email-reply-agent/snippets/send_gate_cases.py` sends nine drafts through the companion's `send_gate`, against its sample thread t-001 and two threads written for the test:

```text
gate hours: 09:00 to 18:00; thread A is t-001
case                  gate says                                                   should  outcome
1 clean reply         ok                                                          send    right
2 new link            BLOCK unknown_url:https://docs.example/terms                block   right
3 new money term      BLOCK introduced_monetary_term                              block   right
4 late hour           BLOCK non_business_hour:21                                  block   right
5 hour without colon  ok                                                          block   missed
6 money in words      ok                                                          block   missed
7 runs past 18:00     ok                                                          block   missed
8 bigger sum          ok                                                          block   missed
9 injected link       BLOCK unknown_url:https://partnerco-support.example/login   block   right
5 of 9 right; 4 slip through
```

The figure below sets the nine cases beside the three checks. The first four are the kind the tests cover. Case 9, an attacker's link in an email, is the first step of [post 23](../23-security/index.md)'s exfiltration chain (section 3); the gate blocks it because its allow-list is the operator's alone (`known_urls`, which `run.py` fills from `EMAILBOT_KNOWN_URLS`), never the email's. Each of the other four slips through a gap: "9 pm" has no colon; "five thousand dollars" has no currency sign; a 30-minute call at 17:45 ends at 18:15; and a thread that mentions a 500-dollar deposit licenses a 50,000-dollar balance, because the money check asks only whether the thread mentions money. A stricter gate compares amounts, reads every way of writing a time, and checks where the slot ends.

![Left, the three checks in order: the operator's URL allow-list, no new money term, hours 09:00 to 18:00. Right, nine draft cases with the gate's verdict: a clean reply passes; a new link, a new dollar term, 21:30 and an injected link are blocked; 9 pm, money in words, a call at 17:45 and a bigger sum pass and are marked missed in red.](diagrams/03-send-gate.svg)

*The gate is a floor under the review, not a substitute for it.*

---

## 10. Observability and evaluation

**One trace per thread.** In a deployment the triager call, memory read, retrieval, drafter call, gate verdict and the person's decision are spans of one trace in the trace store of [post 22](../22-observability/index.md), section 2; opening a bad draft's trace shows which layer was wrong. The four dashboard numbers of [post 22](../22-observability/index.md), section 4, become cost per thread, latency at the 95th percentile (p95), quality, and errors by kind, and quality has a natural source: the share of drafts approved unedited, edited or rejected. The companion prints a line per thread and records nothing more.

**Evaluation.** `eval.py` scaffolds the harness of [post 20](../20-evaluation/index.md) over held-out threads with the user's actual reply and the bucket their behaviour revealed. It reports decision accuracy (the triager's bucket against the revealed one) and two judge scores from 1 to 5, tone fidelity and factual faithfulness, both comparing the draft with the user's actual reply, not with the thread or memory. Two gaps remain: its default fixture file, `data/eval_fixtures.json`, is not shipped, and it has no gate: [post 20](../20-evaluation/index.md), section 4, blocks a change whose metric drops by more than an absolute 0.05, while the scaffold only prints. For tone, the judge failure modes of [post 20](../20-evaluation/index.md), section 6, apply in full.

---

## 11. Deployment: the live steps

Nothing here is in the companion or run in this post; each step is from the provider's documentation, consulted October 2026.

**Gmail.** The worker reads threads and writes drafts through the Gmail API, authorised once with OAuth 2.0, Google's authorisation protocol. Google's "Choose Gmail API scopes" lists `gmail.readonly` as "View your email messages and settings", `gmail.compose` as "Manage drafts and send emails", and `gmail.send` as "Send email on your behalf". The companion's stub requests the first two and notes that `gmail.compose` can send too, so the guarantee that a person ships comes from code that never calls send outside the gated path. "Using OAuth 2.0 for Web Server Applications" says to request `access_type=offline` when the application "needs to refresh access tokens when the user is not present at the browser", and to keep the token in "a secure, long-lived location": a secret manager, never the repository. New mail arrives by polling or by push: Google's "Configure push notifications with the Gmail API" states that "the Gmail API uses the Cloud Pub/Sub API to deliver push notifications" and that the watch must be renewed "at least once every 7 days".

**The worker on Railway.** A Python service (FastAPI in the plan) runs the poll, the pipeline and the gate, and gives the interface endpoints to list pending drafts, approve one (gate, then send) and reject one (record the label). Railway's "Cron Jobs" page sets the terms: a scheduled service is "expected to execute a task, and exit as soon as that task is finished", runs "must be at least 5 minutes apart", schedules are in UTC (Coordinated Universal Time), and if a run is still going "Railway will skip the new cron job". A ten-minute poll fits.

**The approval interface on Vercel.** A small Next.js page lists each pending draft with its thread, with approve, edit and reject. Vercel Functions handle "each incoming request as a new invocation"; the page's functions take the OAuth callback and forward each decision to the worker. The page never calls Gmail or the model, so the send path stays in one place, behind the gate.

**Storage.** A managed PostgreSQL database holds the memory tables, the decision log, the evaluation fixtures and the trace store. Drafting ten held-out threads from a test mailbox and scoring them needs these live steps; the gate blocking an unreviewed send is shown at toy scale in section 9. This post quotes no hosting price: the bill is the hosts' plans plus a model bill that grows with the inbox.

---

## 12. The lesson: every lever has a post

What makes the companion a capstone is not its size but that every choice in it traces to an earlier post. The figure below is the map, with what the companion contains.

![A table of twelve parts of the agent, each with the layer or operation it uses, the posts that teach it, and its state in the companion: five-block system prompt, Gmail tools, recipient memory, prior-reply retrieval, bookend packing, thread compression, triager, JSON replies, send gate, email as data, trace per thread, held-out evaluation.](diagrams/01-every-lever.svg)

*Every row is a decision an earlier post argued for; the right-hand column is how much of it the companion has built.*

The prompt has five blocks because [post 14](../14-system-prompt-as-software/index.md) makes them the checklist for layer 01. The replies are filtered by recipient and bookend-packed because [post 09](../09-select-strategies/index.md) separates candidates from packing. The triager is a sub-agent because [post 13](../13-isolate-strategies/index.md) isolates a task with a clean contract. The gate is code because [post 23](../23-security/index.md) refuses to let the model be the permission system. A component whose reason cannot be named is a candidate for removal.

---

## 13. Where to go next

- **Active learning.** Every edit to a draft is a signal for the prompt's rules or the retrieval filter.
- **Another channel.** Slack or a support queue swap the mailbox driver and the gate's rules; the rest stays.
- **More users.** The memory tables gain a user column and a tenant boundary ([post 24](../24-privacy-and-governance/index.md), section 6).
- **Voice notes.** Transcription feeds layer 06 ([post 19](../19-multimodal-context/index.md), section 6).

---

## 14. Closing: what the series set out to show

[Post 01](../01-why-context-engineering/index.md) argued that "prompt engineering" stopped describing the work once models were given tools, memory and retrieval. Thirty posts later the argument has a shape:

- The model receives six layers, each engineered separately ([post 02](../02-six-layers-of-context/index.md)), and reads them with measured biases ([post 03](../03-how-llms-read-context/index.md)).
- Every token costs money, time and attention ([post 04](../04-tokens-windows-budgets/index.md), [post 05](../05-economics-of-context/index.md)); failures have names and first fixes ([post 06](../06-context-failure-modes/index.md)).
- Write, select, compress and isolate cover the techniques ([posts 07](../07-write-select-compress-isolate/index.md) to [13](../13-isolate-strategies/index.md)), and each layer is its own discipline ([posts 14](../14-system-prompt-as-software/index.md) to [19](../19-multimodal-context/index.md)).
- Production adds evaluation, structured output, observability, security, privacy and the long-context decision ([posts 20](../20-evaluation/index.md) to [25](../25-long-context-vs-rag/index.md)); the workflow puts them in the editor and on a server ([post 26](../26-modern-agentic-workflow/index.md) and [post 27](../27-remote-agentic-workflow/index.md)).
- The three builds, [posts 28](../28-build-rag-chatbot/index.md) to [30](../30-capstone-email-reply-agent/index.md), turn the principles into code a reader can run.

The intended result is a reader who ships LLM (large language model) systems that improve instead of decaying.

---

## 15. Make it run

The companion's seven offline tests (six for the send gate, one for the triager's buckets) run from the series root with no key, because `llm.py` builds the OpenAI client on first use:

```python
def _oai() -> OpenAI:
    """Build the client on first use, so importing this module needs no API key."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client
```

An earlier version built it at import (`_oai = OpenAI()`), so collecting the triager's test failed without `OPENAI_API_KEY`. In PowerShell, set `$env:PYTHONDONTWRITEBYTECODE = "1"` and drop that prefix:

```text
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pydantic --with python-dotenv --with openai python -m pytest -q -p no:cacheprovider -c code/30-email-reply-agent/pyproject.toml code/30-email-reply-agent/tests
```

It ends with `7 passed`. The tests prove that the gate blocks an unknown link, a link quoted in the thread but absent from the operator's list, a new dollar amount and a 22:00 time, and passes a clean draft, a listed link and a 14:00 time, and that the triager has the four documented buckets; nothing about the model's drafts. The three snippets need no key or network:

```text
uv run python posts/30-capstone-email-reply-agent/snippets/drafter_request.py
uv run python posts/30-capstone-email-reply-agent/snippets/send_gate_cases.py
uv run python posts/30-capstone-email-reply-agent/snippets/triage_saving.py
```

They load the companion's offline parts through `snippets/companion.py`, which bypasses the package's imports of the openai, chromadb and voyageai libraries. The live steps are not run here: `uv sync` in the companion directory, a `.env` from `.env.example` with a real `OPENAI_API_KEY` (and `VOYAGE_API_KEY` for meaningful retrieval), then `uv run python -m emailbot.run` triages the two sample threads and drafts the `reply_needed` ones into `data/drafts/`; a Gmail driver, the interface and the worker of section 11 come after.

---

## 16. What can go wrong?

- **A test suite that needs a key to start.** A client built at import fails collection without a key, and continuous integration (CI) without secrets never runs the gate's tests. Create clients on first use.
- **Offline retrieval that is noise.** A fallback on Python's salted `hash()` ranks at random, differently in every process; a deterministic one, such as the companion's hashed word counts, keeps the offline path honest.
- **A placeholder the model reads literally.** Assert after loading that no `{{...}}` remains in a prompt.
- **An allow-list that trusts the attacker.** Links from the thread include a malicious email's links; build the list from the operator's and the user's own.
- **A scope taken for a guarantee.** `gmail.compose` without `gmail.send` still allows sending; only code keeps a person in the loop.
- **A gate trusted as complete.** Four of the snippet's eight harmful drafts pass.

---

## Common pitfalls

1. **Auto-send.** Removing the review to save a click turns every model error into a sent email.
2. **Skipping the triager.** The drafter runs on every newsletter and receipt; cost rises and the review queue fills with unwanted drafts.
3. **Drafting without memory or prior replies.** The drafts are correct and generic, and the user rewrites them.
4. **One rule in two places.** The prompt's hours and the gate's hours drift apart, and the gate passes what the prompt forbids.
5. **No feedback loop.** Approvals and edits are discarded, so the evaluation set never grows.

---

## Further reading

- Google, ["Choose Gmail API scopes"](https://developers.google.com/workspace/gmail/api/auth/scopes), ["Configure push notifications with the Gmail API"](https://developers.google.com/workspace/gmail/api/guides/push) and the [Gmail API reference](https://developers.google.com/gmail/api/reference/rest) (consulted October 2026).
- Google, ["Using OAuth 2.0 for Web Server Applications"](https://developers.google.com/identity/protocols/oauth2/web-server) (consulted October 2026): offline access and refresh tokens.
- Railway, ["Cron Jobs"](https://docs.railway.com/reference/cron-jobs) (consulted October 2026).
- Vercel, ["Vercel Functions"](https://vercel.com/docs/functions) (consulted October 2026).
- The earlier posts cited above, above all posts [14](../14-system-prompt-as-software/index.md), [16](../16-memory-systems/index.md), [20](../20-evaluation/index.md), [22](../22-observability/index.md) and [23](../23-security/index.md).

---

## What to read next

- **[Post 20 - Evaluation](../20-evaluation/index.md):** the regression gate and judge discipline the capstone's evaluation scaffold still lacks, the next thing to build before trusting any change.
- **[Post 01 - Why context engineering, and why now](../01-why-context-engineering/index.md):** the series' opening argument, which reads differently once every part of it has been built.
