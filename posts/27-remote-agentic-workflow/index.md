# 27 - Remote agentic workflow

> **TL;DR.** A coding agent spends most of its time waiting on a model in the cloud, so the agent, the repository and the toolchain can live on a rented server while a laptop or phone only attaches to it. The stack is a cloud virtual machine behind a security group and a scoped instance role, SSH (Secure Shell) with keys only, the agent inside a `tmux` session that outlives every disconnect, and a chat bridge that notifies on three events and carries replies back. At the illustrative sizes of section 6 the model bill is several times the server's, so the case for going remote is the workflow, not the hardware.
>
> **Prerequisites:** [Post 26](../26-modern-agentic-workflow/index.md).
> **Safe to skip?** Skip it if a coding agent already runs on a remote server that survives a closed laptop, notifies only when it needs a person, and holds no credential that reaches production.
>
> **After reading, you will be able to:**
>
> - Decide when moving a coding agent to a remote server pays for the setup, from the task's length, the machine it needs and the devices that drive it.
> - Configure a cloud server behind a security group and an instance role, with key-only SSH and the agent in a tmux session reached over SSH or VS Code.
> - Add a chat bridge that notifies on three events and returns a reply to the running session, and keep it from becoming a way in.
> - Price a month of remote work from an instance's hourly rate and the model's per-million rates, and say which bill dominates.
> - Fence a remote agent box with controls enforced outside the prompt: scoped credentials, network rules, a command deny-list and an audit log.

![Thin clients on the left reach a cloud VM through a dashed security-group boundary by one inbound connection, SSH on port 52222. Inside, a tmux session runs the agent and a chat bridge types replies into it; the agent calls the model API and the bridge polls a chat service, both outbound.](diagrams/00-hero-remote-agentic-workflow.svg)

*Only SSH comes in; the model calls, the package downloads and the chat bridge all go out, so the box needs one inbound rule.*

---

## 1. The question: when is a remote agent worth the setup?

A coding agent waits seconds on a model in the cloud and sends a few kilobytes of text per step, so nothing ties it to the machine the engineer holds. Moving it changes where the loop runs, not the window: the agent assembles the same six layers either way. Three reasons recur.

- **Long-running tasks.** An agent that spends, say, 40 minutes refactoring a module (an illustrative figure) should not need the laptop to stay open. On a server the session runs on through closed lids, lost Wi-Fi and meetings.
- **Bigger machines.** Tests that need 16 GB of memory and a Postgres and Redis stack are unpleasant on a laptop; a `c6i.4xlarge`, with 16 vCPUs (virtual processor threads) and 32 GiB, runs them comfortably (Amazon Web Services (AWS), "Amazon EC2 On-Demand Pricing", consulted October 2026).
- **Several devices.** A task started at the desk is answered from a phone; only the client changes.

A fourth, for regulated or security-conscious teams the main one, is **separating compute from credentials**: the remote box holds tightly scoped credentials in a known network, and the laptop holds none.

Remote does not pay back for quick edit-and-test cycles, where every keystroke's round trip is felt; for demos and pair programming, which want a local interface; or for a prototype whose setup would outlast the work.

---

## 2. The four-box architecture

A remote-agent stack has four boxes, drawn in the figure at the top of the post.

- **Thin client.** A laptop, tablet or phone with SSH and, optionally, VS Code with the Remote - SSH extension.
- **Remote server.** An instance of Amazon EC2 (Elastic Compute Cloud), a Hetzner server, a Google Cloud virtual machine (VM) or a machine at home. The author's rule of thumb is that most coding work fits 4 to 8 vCPUs and 8 to 16 GiB of memory.
- **Coding agent and toolchain.** Claude Code, Aider or Codex CLI in a `tmux` session, with the repository, the toolchain and the test environment.
- **Model API** (application programming interface). The model, for example Claude Opus 4.6 (as of early 2026), reached over HTTPS from the server.

Direction matters more than protocol. Only SSH comes **in**; the model calls, the package downloads and the chat bridge of section 5 all go **out**, and an EC2 security group is stateful, so responses to outbound requests flow back without an inbound rule (AWS, "Amazon EC2 security groups", consulted October 2026). The server therefore needs exactly one inbound rule.

---

## 3. The minimum setup

A reproducible starter, in order:

1. **Provision a server.** A `c6i.xlarge` (4 vCPUs, 8 GiB) on Ubuntu 24.04 is the baseline; a `c6i.large` (2 vCPUs, 4 GiB) suits a light repository; Hetzner's CPX31 has the xlarge's shape for less, when the plan is in stock (section 6).
2. **Lock down SSH.** Keys only, no passwords, no root login, a non-default port, `fail2ban`. The `/etc/ssh/sshd_config` lines:

   ```conf
   Port 52222
   PasswordAuthentication no
   PubkeyAuthentication yes
   PermitRootLogin no
   AllowUsers agent
   ```

   Check the file with `sudo sshd -t` before restarting the server (Ubuntu, "OpenSSH server"), and keep the current session open while a second one tests the new port. To avoid long-lived keys on the laptop, EC2 Instance Connect lets IAM policies decide who may connect and pushes an SSH public key to the instance metadata, where it remains for 60 seconds (AWS, "Connect to your Linux instance using a public IP address and EC2 Instance Connect", consulted October 2026).
3. **Restrict the network and the box's own permissions.** The **security group** is the instance's virtual firewall: inbound TCP only on the SSH port and only from a known address range (an office CIDR, Classless Inter-Domain Routing, block, or a bastion host), never `0.0.0.0/0`; outbound HTTPS for the model API and the package registries. The **IAM instance role** (Identity and Access Management) is the box's cloud identity: software on the instance gets temporary credentials from the role instead of stored access keys (AWS, "IAM roles for Amazon EC2", consulted October 2026), and the role grants only what the work needs, such as one S3 prefix.
4. **Install the toolchain**: `git`, `tmux`, `node`, `python` (through `uv`), `docker`, `gh`, and whatever the project needs.
5. **Install the agent.** Claude Code's documented native installer is `curl -fsSL https://claude.ai/install.sh | bash`; `npm install -g @anthropic-ai/claude-code` still works with Node.js 22 or later (Claude Code, "Advanced setup", consulted October 2026). The key goes in `ANTHROPIC_API_KEY`, read from a file only the agent's user can read, or from a secret manager.
6. **Clone the repository** with a deploy key scoped to it, not a personal SSH key.
7. **Set up `tmux`**: one long-lived session per project, the agent inside it. A minimal `~/.tmux.conf` keeps a long scrollback and shows which project is attached:

   ```conf
   set -g history-limit 50000
   set -g mouse on
   set -g status-left "#S "
   ```

8. **Connect from VS Code.** The Remote - SSH extension installs the VS Code Server on the remote machine and runs commands and extensions there (VS Code, "Remote Development using SSH", consulted October 2026).

Worth adding the same day: a progress file the agent writes at the end of each session, a write destination in [post 08](../08-write-strategies/index.md)'s sense that the next session reads back.

---

## 4. Persistence and handoff

The point of the remote setup is that sessions persist. A session is started once and attached to from anywhere:

```bash
tmux new -s acme-api        # on the server, once: create the session
claude                      # start the agent inside it
# detach with Ctrl-b then d, or simply close the laptop
tmux attach -t acme-api     # later, from any client: the same session
```

Three things survive a disconnect. **The `tmux` session** outlives SSH. **The agent's conversation** survives because the process never stopped; if it does end (a crash, a reboot), Claude Code keeps each session's transcript on disk and `claude --continue` loads the most recent conversation in the directory (Claude Code, "CLI reference", consulted October 2026). **The shell history, working directory and processes in flight** stay alive in their panes.

So the engineer can disconnect, change device and pick up where the work stood; the agent cannot tell that the client changed. The figure below follows one session through a working day reached from three clients.

![A time line with three client lanes above two bars. The laptop attaches and starts the task, then closes. The phone gets a blocked notification, replies through the bridge, and later a complete notification. VS Code on a second computer then attaches. The tmux session runs throughout, the task inside it until it completes.](diagrams/01-persistence-and-handoff.svg)

*Clients come and go; the session and the task inside it run on without them.*

One habit keeps this tidy: **one `tmux` session per project**, so each agent's window holds one project's material and stays clear of the distraction of [post 06](../06-context-failure-modes/index.md).

---

## 5. Notifications and asynchronous oversight

The agent must reach out when it needs a person, and only then: **notify on three events**, task complete, blocked on a question, and an error that needs a person. Notifying on every step trains the reader to ignore the channel.

In Claude Code two of the three are hook events ([post 26](../26-modern-agentic-workflow/index.md) introduces hooks). `Stop` fires when Claude finishes responding: task complete. `Notification` fires when Claude Code sends a notification, and a matcher on its type, such as `permission_prompt` or `idle_prompt`, picks out an agent waiting on a person: blocked (Claude Code, "Hooks reference", consulted October 2026). The third is explicit: the agent gets a `notify_user` tool for an error it cannot resolve. The hook or tool posts to a Telegram bot (*"Tests passing on PR #432, ready to merge?"*), Slack, Discord or email.

The reply path is the fiddly half. A bridge cannot write to the agent's standard input, which is the terminal `tmux` holds. It either drives the terminal, typing the reply into the agent's `tmux` pane as a person would, or returns the reply as a tool result on the next turn. A loop of the first kind is short; `telegram_get_reply` stands for a function that long-polls the Telegram Bot API's `getUpdates` and keeps only the engineer's own chat:

```bash
while true; do
  reply=$(telegram_get_reply)                 # placeholder: long-poll, one allowed chat id only
  if [ -n "$reply" ]; then
    tmux send-keys -t acme-api -l -- "$reply" # -l literal; -- ends the options
    tmux send-keys -t acme-api Enter
  fi
  sleep 2
done
```

Without `-l`, `tmux` looks each argument up as a key name first, so a reply reading `C-c` would arrive as an interrupt. Polling matters too: the Bot API offers long polling with `getUpdates` or a webhook, which needs an inbound HTTPS port (443, 80, 88 or 8443) (Telegram, "Bot API", consulted October 2026); polling keeps section 2's single inbound rule.

Community bridges package the pattern: Claude-Code-Remote, a GitHub project (changelog to August 2025), notifies from the `Stop` hook by email, Telegram or LINE and injects replies into the `tmux` session or a pseudo-terminal after checking the sender's id. Anthropic's own Remote Control connects claude.ai/code or the Claude app to a Claude Code session on the engineer's machine, which makes outbound HTTPS requests only and never opens inbound ports; it needs a Pro, Max, Team or Enterprise plan and does not support API keys (Claude Code, "Remote Control", consulted October 2026). It is the stack's web access, and it fits the one-inbound-rule box.

---

## 6. The cost model

A remote setup has two bills. The server rates are AWS On-Demand Linux rates for US East (N. Virginia) and Hetzner's CPX31 price for new US orders from 15 June 2026, excluding VAT and the IPv4 address (AWS, "Amazon EC2 On-Demand Pricing"; Hetzner, "Price adjustment"; both consulted October 2026). The model is Claude Opus 4.6 at 5 dollars per million input tokens and 25 per million output, as of early 2026, with a five-minute cache write at 1.25 times and a cache read at 0.1 times the base input price, the rate for most models (Anthropic, "Pricing" and "Prompt caching", consulted October 2026; [post 05](../05-economics-of-context/index.md), sections 2 and 4). The task sizes are illustrative (64 calls per thirty-minute task, 90% of each call's input read from the cache and the rest written to it, four tasks a day on 22 working days). Run from the series root as `uv run python posts/27-remote-agentic-workflow/snippets/remote_costs.py`, the snippet prints:

```text
EC2 On-Demand, Linux, US East (N. Virginia), consulted October 2026
  c6i.large     2 vCPU   4 GiB  0.085 $/h    62.05 $ a 730-hour month
  c6i.xlarge    4 vCPU   8 GiB  0.170 $/h   124.10 $ a 730-hour month
  c6i.2xlarge   8 vCPU  16 GiB  0.340 $/h   248.20 $ a 730-hour month
  c6i.4xlarge  16 vCPU  32 GiB  0.680 $/h   496.40 $ a 730-hour month
  c6i.xlarge stopped outside working hours, 176 h a month: 29.92 $
Hetzner CPX31, 4 vCPU, 8 GB, US, from 15 June 2026: 73.49 $ a month (c6i.xlarge all month: 124.10)
egress: 20 GB a month costs 0.00 $; 150 GB would cost 4.50 $

one thirty-minute task, Claude Opus 4.6: 64 calls of 50,000 tokens in and 1,000 out
  uncached                 input 16.00 + output 1.60 = 17.60 $
  90% read from the cache  read 1.44 + write 2.00 + output 1.60 = 5.04 $
  c6i.xlarge for the same half hour: 0.085 $; the model costs 59 times as much

a month of 88 such tasks: model 443.52 $, against the server 124.10 (all month) or 29.92 (working hours)
```

A server costs rate times hours: $0.17 \times 730 = 124.10$ dollars for a month left running. Egress barely registers: AWS gives the first 100 GB a month to the internet free, then charges 0.09 dollars per GB, so an illustrative 20 GB costs nothing. With the cache, one task's input is $64 \times 45{,}000 \times 0.5 / 10^6 = 1.44$ dollars of reads plus $64 \times 5{,}000 \times 6.25 / 10^6 = 2.00$ of writes, against $16.00$ uncached. The figure below sets the month side by side.

![Five bars of dollars a month. Solid, from cited rates: c6i.4xlarge all month 496.40, c6i.xlarge all month 124.10, Hetzner CPX31 73.49, c6i.xlarge for 176 working hours 29.92. Dashed, illustrative: the model bill for 88 cached tasks on Claude Opus 4.6, 443.52.](diagrams/02-cost-of-a-month.svg)

*The model bill outweighs a right-sized server several times over; only a large instance left running rivals it.*

**Measure both sides**: the trace store of [post 22](../22-observability/index.md), section 2, records the model cost per call, and the cloud bill records the server. An idle server can be stopped outside working hours, at a price: a stopped instance loses its memory, so the `tmux` session and the agent end and the conversation returns only through `claude --continue`; it gets a new public IPv4 address at start unless an Elastic IP is attached; and its EBS (Elastic Block Store) volumes are still billed (AWS, "How EC2 instance stop and start works", consulted October 2026). If the model dominates, the levers are the series' own: a cached prefix (post 05), compression ([post 12](../12-compress-strategies/index.md)) and sub-agent budgets ([post 13](../13-isolate-strategies/index.md), section 5).

---

## 7. Security on a remote agent

The box runs an agent with a shell and some credentials; the table below lists every control in one place, with what it fences and what enforces it.

![A table of seven controls: a security group, key-only SSH with MFA or Instance Connect, a scoped instance role, a deny-list hook, read-only mounts, staging-only credentials and an audit log, each with what it fences and what enforces it outside the model.](diagrams/03-remote-controls.svg)

*Every control is enforced outside the model, so nothing the model reads can switch it off.*

- **No production credentials on the development box.** Staging credentials only; production is reached through the continuous-integration and continuous-deployment (CI/CD) path, never through the agent.
- **Read-only mounts** for what the agent must not write: vendored directories, generated code, secrets.
- **A deny-list of dangerous commands at the hook level**: no `rm -rf /`, no `git push --force` to `main`, no `sudo`. A Claude Code `PreToolUse` hook runs before a tool call and blocks it by exiting with code 2 or returning a `deny` decision (Claude Code, "Hooks reference", consulted October 2026). A deny-list matches text and a command can be spelled many ways, so it is a backstop behind the credentials and mounts.
- **MFA on SSH** (multi-factor authentication) for the human side.
- **An audit log** of every command the agent ran, with timestamp and user, kept where the agent's user cannot edit it.

These are [post 23](../23-security/index.md)'s defences on a box. The role, the mounts and the staging credentials bound each tool's blast radius (D2: a sandbox in post 23's security sense, not post 13's output-scoping sense), and the hook checks a proposed action in code (D1). The chat bridge adds a boundary a laptop lacks: a reply from the engineer's chat is `user` content in post 23's trust-tag terms, a message from anyone else is `external` and never reaches `send-keys` (D3, post 23, section 5).

---

## 8. The mobile workflow

A **phone can be the thin client**, which works better than it sounds when the agent does most of the typing:

- **An SSH client on the phone** (Termius, Blink Shell, JuiceSSH), attached to the `tmux` session.
- **A skill** telling the agent its reader is on a phone: shorter answers, smaller code blocks, more confirmations. A skill is a directory with a `SKILL.md` whose name and description load up front ([post 14](../14-system-prompt-as-software/index.md), section 4).
- **The chat bridge or Remote Control** for quick replies without SSH.

An engineer can then review a pull request, have the agent fix a typo and run the tests, and merge from a 6-inch screen: the agent works and the person approves.

The lab for this post, described as a procedure and not reported as a run: the minimum setup on one small VM, a thirty-minute task started in `tmux`, the laptop closed, and the session resumed from a second device with the task still running.

---

## 9. What can go wrong?

- **The agent started outside `tmux`.** Closing the laptop ends SSH and the agent with it; next morning the task stopped where the lid closed.
- **A reply typed into the wrong place.** The agent has exited, the bridge types the next reply anyway, and it runs as a shell command. The bridge checks that the pane runs the agent (`tmux display -p -t acme-api '#{pane_current_command}'`) first.
- **A bridge that accepts any chat.** Whoever finds the bot can instruct an agent with a shell; the symptom is commits nobody asked for. Only the engineer's chat id is accepted.
- **Locked out after moving the SSH port.** The security group still allows only port 22, or a typo stops `sshd`; the connection times out. Open the new port first, run `sudo sshd -t`, keep one session open.
- **A schedule that kills the session.** The box is stopped each evening, and each morning the `tmux` session, the agent and the test run are gone and the address has changed.

---

## Common pitfalls

1. **Production credentials on the agent box.** A bug in the agent, or an attack on it, reaches production.
2. **No deny-list on dangerous commands.** Eventually the agent runs the wrong one.
3. **A personal SSH key as the deploy key.** The audit trail is lost, and a leak widens the blast radius.
4. **An API key in a world-readable file.** Every process on the box can read it.
5. **Forgetting to downscale.** A `c6i.4xlarge` left running costs 496.40 dollars a month at section 6's rate.

---

## Further reading

- AWS, *"Amazon EC2 On-Demand Pricing"*, and Hetzner, *"Price adjustment"* (consulted October 2026): the rates of section 6.
- Anthropic, *"Pricing"* and *"Prompt caching"* (Claude API documentation, consulted October 2026).
- AWS EC2 documentation (consulted October 2026): *"Amazon EC2 security groups"*, *"IAM roles for Amazon EC2"*, *"Connect to your Linux instance using a public IP address and EC2 Instance Connect"*, *"How EC2 instance stop and start works"*.
- VS Code, *"Remote Development using SSH"*; Claude Code, *"Advanced setup"*, *"CLI reference"*, *"Hooks reference"* and *"Remote Control"*; Telegram, *"Bot API"* (all consulted October 2026).
- The `tmux` manual page: `new-session`, `attach-session`, `send-keys -l`.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 28 - Build #1: RAG chatbot from scratch](../28-build-rag-chatbot/index.md):** the first build, a natural first task to run on the remote box.
- **[Post 23 - Security and prompt injection](../23-security/index.md):** the four defences behind section 7's controls and the trust tag the chat bridge needs.
