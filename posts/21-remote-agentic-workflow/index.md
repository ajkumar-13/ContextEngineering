# 21 · Remote agentic workflow

> **TL;DR.** Modern coding agents are *latency-sensitive* and *bandwidth-light*: the model lives in the cloud, but the agent process, the codebase, and the toolchain can run anywhere with shell access. The pattern that has emerged for serious work — long-running tasks, large codebases, expensive local hardware not required — is to put **the agent on a remote server** and connect to it from a thin client (a laptop, a phone, a terminal). This post covers the architecture, the standard tooling (`tmux`, `ssh`, VS Code Remote, Telegram bridges), and the ergonomic pieces (notifications, session persistence, multi-device handoff) that make remote agentic work feel native.
>
> **Reading time:** ~11 minutes.
>
> **After reading this you will be able to:**
> - Decide when remote agentic work is worth the setup.
> - Configure a remote-agent stack (EC2 or equivalent + tmux + SSH + VS Code Remote).
> - Add the ergonomic layers (Telegram notifications, web access) that make it usable from anywhere.

---

## 1. Why remote

Three reasons that recur, in roughly the order teams discover them.

- **Long-running tasks.** A coding agent that takes 40 minutes to refactor a module should not require the user's laptop to stay open. On a server, the session keeps running through closed lids, lost Wi-Fi, and meeting blocks.
- **Bigger machines.** A repository whose tests need 16 GB of RAM and a Postgres + Redis stack is unpleasant on a laptop. A `c6i.4xlarge` is unpleasant for nobody.
- **Multi-device.** Start a task from the desk; check on it from the couch; respond to its question from a phone in a coffee queue. The session is the same; only the client changes.

A fourth, less universal reason: **separation of compute from credentials**. The remote box has tightly scoped credentials and lives in a known network; the laptop has none. For some teams (regulated industries, security-conscious shops) this is the headline benefit.

The cases where remote does *not* pay back: short, interactive sessions with quick edit-test cycles where the round-trip latency of every keystroke matters; demos and pair-programming that benefit from the local UI's responsiveness; greenfield prototyping where setup overhead exceeds the work itself.

---

## 2. The architecture

A working remote-agent stack has four boxes:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Thin client │ →   │   Remote     │  ↔  │  Coding      │  ↔  │  LLM API     │
│ laptop/phone │ SSH │   server     │     │  agent +     │     │ (Claude,     │
│              │     │ (tmux + IDE) │     │  toolchain   │     │  GPT, etc.)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

- **Thin client.** A laptop, a tablet, a phone. Needs SSH and (optionally) VS Code Remote. Anything that can hold an SSH session can drive the agent.
- **Remote server.** An EC2 instance, a Hetzner box, a Google Cloud VM, a homelab machine. Sized to the workload (most coding work is fine on a 4–8 core box with 16 GB RAM).
- **Coding agent + toolchain.** The actual work happens here: Claude Code or Aider or Codex CLI in a `tmux` session, the repository checked out, the language toolchain installed, the test environment configured.
- **LLM API.** The model. Reached via HTTPS. The same provider you would use locally.

The four boxes communicate over standard protocols: SSH between client and server; HTTPS between server and LLM API. No special networking, no VPN required (though one is wise for production keys), no novel security stance.

---

## 3. The minimum setup

A reproducible starter that takes about 30 minutes:

1. **Provision a server.** A `c6i.xlarge` EC2 instance (Ubuntu 24.04) is overkill for most coding work and a good baseline. Cheaper providers (Hetzner, DigitalOcean) often beat AWS on $/core for this use case.
2. **Lock down SSH.** Key-based auth only; no password auth; non-default port; `fail2ban` installed. The agent will be running with elevated trust; treat the box accordingly.
3. **Install the toolchain.** Whatever your project needs. A minimal modern stack: `git`, `tmux`, `node`, `python` (via `uv` or `pyenv`), `docker`, the language's package manager, `gh` for GitHub access.
4. **Install the agent.** `npm i -g @anthropic-ai/claude-code` (or the equivalent for your tool of choice). Configure the API key via the host's standard mechanism (environment variable from a `.env` file with strict permissions, ideally a secret manager).
5. **Clone the repo.** Use a deploy key scoped to the repository, not your personal SSH key.
6. **Set up `tmux`.** A long-lived session per project (`tmux new -s acme-api`); the agent runs inside it; closing SSH does not kill the session.
7. **Connect from VS Code Remote.** Install the Remote-SSH extension; point it at the server; the editor experience is local-feeling, the work happens on the server.

Optional but worth adding the same day:

- **A `tmux` window layout** with the editor in one pane and the agent in another, so context-switching is fast.
- **Shell aliases** for the agent commands you run constantly.
- **A daily-journal file** the agent writes to at the end of each session.

---

## 4. Persistence and handoff

The killer feature of the remote setup: sessions persist. The mechanics:

- **`tmux` sessions** outlive SSH. `tmux attach -t acme-api` reconnects to whatever was running.
- **The agent's conversation history** persists in its own state file. Reattaching shows the conversation as it was.
- **The shell history, the working directory, the in-flight processes** all stay alive.

Combined: the user can disconnect, switch devices, reconnect from anywhere, and pick up *exactly* where they left off. The agent does not know it switched users.

A useful habit: **one `tmux` session per active project**. Switching projects means switching sessions, not editor tabs. The agent's context per session stays focused.

---

## 5. Notifications and async oversight

The remote agent runs while the user is doing other things. The pattern that makes it usable: **the agent reaches out when it needs the user**. A small bridge does this:

- **Telegram bot** for push notifications. The agent calls a `notify_user` tool; the tool posts to a Telegram chat the user is in. *"Tests passing on PR #432, ready to merge?"*
- **Slack / Discord** equivalents work the same way.
- **Email** is the lowest-friction option for one-way "task complete" alerts.

The user replies on the same channel; a small daemon on the server polls the channel and pipes responses back into the agent's stdin. The whole thing is a few hundred lines of code; several open-source bridges (e.g. *OpenClaude*, *agent-bridge*, the Aider Telegram integration) do it out of the box.

The discipline that keeps notifications useful: **the agent only notifies on three events** — task complete, blocked on a question, error that needs human attention. Notifying on every step trains the user to ignore the channel.

---

## 6. The cost model

A typical remote setup runs around $30–80 / month for the server (EC2 `c6i.xlarge` sustained-use; Hetzner CPX31 cheaper) plus the LLM API bill, which dominates everything else for a productive engineer ($200–1 000 / month on Claude Code or Cursor Ultra at full use).

The savings over a beefy local laptop are not the point; the point is the *workflow*. An hour of agent-driven refactoring you can kick off and check on later is worth a lot more than the $1 of compute it cost to run.

A useful reality check: **measure both sides**. The trace store from Post 17 captures the LLM cost; standard cloud billing captures the server cost. If the server is idle most of the time, downscale or use a spot/preemptible instance. If the LLM cost is dominating, look at compression, caching, and sub-agent budgets.

---

## 7. Security on a remote agent

The remote box runs an agent with shell access and (probably) deploy credentials. A short list of the controls that matter:

- **No production credentials in the dev box.** Use staging credentials; promote to production via your normal CI/CD path, not via the agent.
- **Read-only filesystem mounts** for anything sensitive the agent should not write to (vendor directories, generated code, secrets).
- **A deny-list of dangerous commands** at the hook level (Post 20, §6) — the agent cannot `rm -rf /`, cannot `git push --force` to `main`, cannot `sudo`.
- **MFA-protected SSH** for the human side of the connection.
- **Audit log** of every shell command the agent ran, with timestamp and user. Saves the on-call engineer's evening when a bug needs to be reproduced.

The threat model on a remote box is the same as on a laptop, *plus* the network. The defences are standard server hygiene with the additional thought that the agent itself is a (mostly) trusted automated user.

---

## 8. The mobile workflow

A pattern several practitioners have made productive: **use a phone as the thin client**. The mobile experience for a coding agent is surprisingly good when the agent does most of the typing.

The setup:

- **SSH client on phone** (Termius, Blink Shell, JuiceSSH).
- **`tmux` session** on the server, attached over SSH.
- **A skill** that knows the user is on mobile (smaller code blocks, shorter responses, more confirmation prompts).
- **Telegram bridge** for notifications and quick replies without opening SSH at all.

The result is a workflow where you can review a PR, ask the agent to fix a typo, have it run the tests, and merge — all from a 6-inch screen. The leverage is real because the *agent* is doing the work; the user is mostly approving.

This is not a primary workflow for most engineers; it is an *available* one, which is itself the point. Remote agents stop being tied to the desk.

---

## Common pitfalls

- **Production credentials on the agent box.** A bug-or-attack on the agent reaches production.
- **No `tmux`.** Disconnect kills the session; the work is lost.
- **Notifying on every step.** The user trains themselves to ignore the channel.
- **No deny-list on dangerous commands.** Eventually the agent runs the wrong one.
- **Personal SSH key as the deploy key.** Loses the audit trail; widens the blast radius if compromised.
- **Forgetting to downscale.** A `c6i.4xlarge` running idle for a month is real money.

---

## Further reading

- AWS, *"Connect using EC2 Instance Connect"* docs (2024) — the no-key SSH path.
- VS Code, *"Remote development over SSH"* docs (latest).
- Aider docs, *"Running Aider on a remote server"* (2024).
- Anthropic, *"Claude Code on a server"* (community guides, 2024–25).
- *OpenClaude / claude-code-remote* (community projects) — Telegram and web bridges.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 22 — Build a RAG chatbot](../22-build-rag-chatbot/index.md)** — the first build, end-to-end.
- **[Post 23 — Build an MCP server](../23-build-mcp-server/index.md)** — the second build.
- **[Post 24 — Capstone: email reply agent](../24-capstone-email-reply-agent/index.md)** — the everything-together project.
