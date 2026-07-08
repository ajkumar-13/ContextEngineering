# 27 · Remote agentic workflow

> **TL;DR.** Modern coding agents are *latency-sensitive* and *bandwidth-light*: the model lives in the cloud, but the agent process, the codebase, and the toolchain can run anywhere with shell access. The pattern that has emerged for serious work — long-running tasks, large codebases, expensive local hardware not required — is to put **the agent on a remote server** and connect to it from a thin client (a laptop, a phone, a terminal). This post covers the architecture, the standard tooling (`tmux`, `ssh`, VS Code Remote, Telegram bridges), and the ergonomic pieces (notifications, session persistence, multi-device handoff) that make remote agentic work feel native.
>
> **After reading this you will be able to:**
> - Decide when remote agentic work is worth the setup.
> - Configure a remote-agent stack (EC2 or equivalent + tmux + SSH + VS Code Remote).
> - Add the ergonomic layers (Telegram notifications, web access) that make it usable from anywhere.

![Network diagram: a laptop connects over SSH to a cloud VM running a tmux agent session, with a chat bridge relaying messages and a security-group boundary around the VM.](diagrams/00-hero-remote-agentic-workflow.svg)
*A small remote setup keeps the agent working after the laptop closes.*

---

## 1. Why remote

Three reasons that recur, in roughly the order teams discover them.

- **Long-running tasks.** A coding agent that spends, say, 40 minutes refactoring a module (an illustrative figure, not a benchmark) should not require the user's laptop to stay open. On a server, the session keeps running through closed lids, lost Wi-Fi, and meeting blocks.
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
│              │     │ (tmux + IDE) │     │  toolchain   │     │  Gemini …)   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

- **Thin client.** A laptop, a tablet, a phone. Needs SSH and (optionally) VS Code Remote. Anything that can hold an SSH session can drive the agent.
- **Remote server.** An EC2 instance, a Hetzner box, a Google Cloud VM, a homelab machine. Sized to the workload (most coding work is fine on a 4–8 core box with 16 GB RAM).
- **Coding agent + toolchain.** The actual work happens here: Claude Code or Aider or Codex CLI in a `tmux` session, the repository checked out, the language toolchain installed, the test environment configured.
- **LLM API.** The model (Claude Opus 4.x, Sonnet 4.5, Gemini 2.5, a frontier GPT model). Reached via HTTPS. The same provider the user would reach locally.

The four boxes communicate over standard protocols: SSH between client and server; HTTPS between server and LLM API. No special networking, no VPN required (though one is wise for production keys), no novel security stance.

---

## 3. The minimum setup

A reproducible starter that takes about 30 to 45 minutes:

1. **Provision a server.** A `c6i.xlarge` EC2 instance (Ubuntu 24.04) is a sensible baseline; a smaller `c6i.large` is enough for most coding work. Cheaper providers (Hetzner, DigitalOcean) often beat AWS on price per core for this use case (see the pricing pages in Further reading; treat the ranges in §6 as illustrative, not measured).
2. **Lock down SSH.** Key-based auth only; no password auth; non-default port; `fail2ban` installed. The agent will be running with elevated trust; treat the box accordingly. The relevant `/etc/ssh/sshd_config` lines:

   ```conf
   Port 52222
   PasswordAuthentication no
   PubkeyAuthentication yes
   PermitRootLogin no
   AllowUsers agent
   ```

3. **Restrict the network and the machine's own permissions.** On EC2 this is two pieces. The **security group** is the instance firewall: allow inbound TCP only on the SSH port, and only from a known IP range (a home or office CIDR, or a bastion), not `0.0.0.0/0`; allow outbound `443` for the LLM API and package registries. The **IAM instance role** is the box's own cloud identity: attach a role scoped to exactly what the workload needs (read a specific S3 prefix, pull from one ECR registry) rather than baking long-lived access keys into the box. Scoped credentials that live on the server and never touch the laptop are the whole point of the separation-of-credentials benefit from §1.
4. **Install the toolchain.** Whatever the project needs. A minimal modern stack: `git`, `tmux`, `node`, `python` (via `uv` or `pyenv`), `docker`, the language's package manager, `gh` for GitHub access.
5. **Install the agent.** `npm i -g @anthropic-ai/claude-code` (or the equivalent for the tool of choice). Configure the API key via the host's standard mechanism (environment variable from a `.env` file with strict permissions, ideally a secret manager).
6. **Clone the repo.** Use a deploy key scoped to the repository, not a personal SSH key.
7. **Set up `tmux`.** A long-lived session per project (`tmux new -s acme-api`); the agent runs inside it; closing SSH does not kill the session. A minimal `~/.tmux.conf` that survives reconnects and shows which project is attached:

   ```conf
   set -g history-limit 50000
   set -g mouse on
   set -g status-left "#S "
   ```

8. **Connect from VS Code Remote.** Install the Remote-SSH extension; point it at the server; the editor experience is local-feeling, the work happens on the server.

Optional but worth adding the same day:

- **A `tmux` window layout** with the editor in one pane and the agent in another, so context-switching is fast.
- **Shell aliases** for the agent commands the user runs constantly.
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

The reply path is the fiddly half. A running agent is usually mid-turn, so a bridge cannot just write to its `stdin` and expect the text to land in the right place. In practice the bridge either drives the agent's terminal directly (a daemon polls the chat, then writes the reply into the agent's `tmux` pane with `tmux send-keys -t acme-api "$reply" Enter`, which is exactly what a human would type), or it exposes the reply as a tool result the agent reads on its next turn. A poll-and-inject loop is short:

```bash
while true; do
  reply=$(telegram_get_updates)          # long-poll the chat
  [ -n "$reply" ] && tmux send-keys -t acme-api "$reply" Enter
  sleep 2
done
```

Several open-source bridges do this out of the box. `claude-code-remote` (sometimes abbreviated CCO) and *OpenClaude* are the community projects most people start from: they run a small server next to the agent, register a `notify_user` tool the agent can call, and relay replies back through a Telegram or web front end using the `send-keys` approach above. Setting one up is: clone the project, set a bot token and the target `tmux` session in its config, and run its daemon under the same `tmux` server as the agent. The Aider Telegram integration is the equivalent for that host.

The discipline that keeps notifications useful is that **the agent only notifies on three events**: task complete, blocked on a question, error that needs human attention. Notifying on every step trains the user to ignore the channel.

---

## 6. The cost model

The numbers below are illustrative order-of-magnitude figures, not measured benchmarks; the live prices are on each provider's pricing page (see Further reading). As a rough rule of thumb, a remote setup runs on the order of tens of dollars a month for the server (an EC2 `c6i.xlarge` on sustained use; a Hetzner CPX31 is cheaper for comparable cores) plus the LLM API bill, which dominates everything else for a productive engineer. That LLM bill, again illustratively, can run from a couple of hundred dollars a month up into four figures for a heavy user on a metered API or a premium coding-agent subscription; at Sonnet-tier input pricing, roughly $3 per million input tokens ([Post 04](../04-tokens-windows-budgets/index.md), §3), a single 1M-token session costs about $3, so the monthly total is driven by session volume more than by any one call.

The savings over a beefy local laptop are not the point; the point is the *workflow*. An hour of agent-driven refactoring the user can kick off and check on later is worth a lot more than the dollar or so of compute it cost to run.

A useful reality check: **measure both sides**. The trace store from Post 22 captures the LLM cost; standard cloud billing captures the server cost. If the server is idle most of the time, downscale or use a spot/preemptible instance. If the LLM cost is dominating, look at compression, caching, and sub-agent budgets.

---

## 7. Security on a remote agent

The remote box runs an agent with shell access and (probably) deploy credentials. A short list of the controls that matter:

- **No production credentials in the dev box.** Use staging credentials; promote to production via the normal CI/CD (continuous-integration/continuous-deployment) path, not via the agent.
- **Read-only filesystem mounts** for anything sensitive the agent should not write to (vendor directories, generated code, secrets).
- **A deny-list of dangerous commands** at the hook level (Post 26, §6) — the agent cannot `rm -rf /`, cannot `git push --force` to `main`, cannot `sudo`.
- **MFA-protected SSH** (multi-factor authentication) for the human side of the connection.
- **Audit log** of every shell command the agent ran, with timestamp and user. Saves the on-call engineer's evening when a bug needs to be reproduced.

The threat model on a remote box is the same as on a laptop, *plus* the network. The defences are standard server hygiene with the additional thought that the agent itself is a (mostly) trusted automated user.

---

## 8. The mobile workflow

A pattern several practitioners have made productive: **use a phone as the thin client**. The mobile experience for a coding agent is surprisingly good when the agent does most of the typing.

The setup:

- **SSH client on phone** (Termius, Blink Shell, JuiceSSH).
- **`tmux` session** on the server, attached over SSH.
- **A skill** ([Post 26](../26-modern-agentic-workflow/index.md), §4: a small Markdown file that packages one agent capability) that knows the user is on mobile: smaller code blocks, shorter responses, more confirmation prompts.
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

- AWS, *"Amazon EC2 On-Demand pricing"* (pricing page, 2025–26): the source for the `c6i` instance figures cited in §6.
- Hetzner, *"Cloud pricing"* (pricing page, 2025–26): the source for the CPX31 comparison in §6.
- Anthropic, *"Pricing"* and *"Prompt caching"* docs (2025–26): the per-million and cached-read figures behind the §6 rule of thumb.
- AWS, *"Connect using EC2 Instance Connect"* docs (2025): the no-key SSH path.
- VS Code, *"Remote development over SSH"* docs (2025–26).
- Aider docs, *"Running Aider on a remote server"* (2025).
- Anthropic, *"Claude Code"* docs and community server guides (2025–26).
- *OpenClaude / claude-code-remote* (community projects): the Telegram and web bridges from §5.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 26 — The modern agentic workflow](../26-modern-agentic-workflow/index.md)**: the same workflow on a local machine; the loop, skills, and hooks this post moves to a server.
- **[Post 28 — Build a RAG chatbot](../28-build-rag-chatbot/index.md)**: the first build, end-to-end.
- **[Post 29 — Build an MCP server](../29-build-mcp-server/index.md)**: the second build. MCP (Model Context Protocol) is the standard tool-server interface.
- **[Post 30 — Capstone: email reply agent](../30-capstone-email-reply-agent/index.md)**: the everything-together project.
