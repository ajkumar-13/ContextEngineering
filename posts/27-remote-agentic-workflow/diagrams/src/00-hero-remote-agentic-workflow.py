"""Post 27 hero: the four-box remote architecture, with one inbound rule and everything else outbound.

Run from the series root:  uv run python posts/27-remote-agentic-workflow/diagrams/src/00-hero-remote-agentic-workflow.py
Writes posts/27-remote-agentic-workflow/diagrams/00-hero-remote-agentic-workflow.svg.

Numbers drawn: the SSH port 52222 (the sshd_config block of section 3) and HTTPS port 443 (the protocol's port;
section 3's outbound rule). The boxes, the direction of every connection and the bridge's polling are sections
2, 3 and 5; the phrases are asserted against the body. No layer of the window appears, so no role colour is used:
everything is neutral.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("Port 52222", "Only SSH comes **in**", "all go **out**", "exactly one inbound rule",
               "long-polls the Telegram Bot API's `getUpdates`", "**IAM instance role**",
               "typing the reply into the agent's `tmux` pane", "drawn in the figure at the top of the post",
               "Claude Opus 4.6 (as of early 2026)"):
    assert phrase in BODY, phrase

desc = ("Four boxes from left to right. Thin clients: a laptop with SSH or VS Code, and a phone with an SSH app "
        "and a chat app. A dashed security-group boundary admits one inbound connection, SSH on port 52222. "
        "Inside it a cloud VM with a scoped instance role holds a tmux session running the coding agent with the "
        "repository and the toolchain, and a chat bridge that types replies into the session with send-keys. "
        "Both reach out: the agent to the model API, Claude Opus 4.6 or a peer, over HTTPS on port 443, and the "
        "bridge to a chat service such as the Telegram Bot API, which it polls. The chat service carries "
        "notifications to the phone and replies back.")
fig = Figure("00-hero-remote-agentic-workflow", "Only SSH comes in; everything else goes out", desc,
             subtitle="The four boxes of a remote agent: thin clients, the server, the agent and its toolchain, "
                      "the model API.",
             data_w=True)


def box(b, head, lines, outline="rule", fill="surface"):
    fig.fill(b, fill, radius=8, fit=False)
    fig.outline(b, outline, radius=8)
    fig.text(b.x + 16, b.y + 28, head, "head")
    for k, s in enumerate(lines):
        fig.text(b.x + 16, b.y + 52 + 24 * k, s, "label")


# thin clients
fig.text(40, 184, "Thin clients", "head")
laptop = Box(40, 200, 120, 104)
phone = Box(40, 336, 120, 80)
box(laptop, "Laptop", ["SSH", "VS Code"], fill="neutral-soft", outline="border")
box(phone, "Phone", ["SSH, chat"], fill="neutral-soft", outline="border")

# the security group and the VM
SG = Box(240, 112, 416, 344)
fig.outline(SG, "ink-muted", width=1.5, dash="proj", radius=8)
fig.text(SG.x + 16, SG.y + 24, "Security group: one inbound rule", "note")
vm = Box(256, 144, 384, 296)
fig.fill(vm, "neutral-soft", radius=8, fit=False)
fig.outline(vm, "border", radius=8)
fig.text(vm.x + 16, vm.y + 32, "Cloud VM", "head")
fig.text(vm.right - 16, vm.y + 32, "instance role: scoped", "note", anchor="end")
tmux = Box(280, 200, 336, 104)
box(tmux, "tmux session", ["coding agent", "repository, toolchain"])
bridge = Box(280, 344, 336, 72)
box(bridge, "Chat bridge", ["polls, types replies"])
fig.arrow((bridge.right - 72, bridge.y - 2), (bridge.right - 72, tmux.bottom + 2), label="send-keys", side="left")

# the outside services
model = Box(768, 200, 152, 104)
box(model, "Model API", ["Claude Opus 4.6", "or a peer"])
chat = Box(768, 344, 152, 72)
box(chat, "Chat service", ["Telegram Bot API"])

# connections: one in, three out
fig.arrow((laptop.right + 2, 252), (vm.x - 2, 252))
fig.text(200, 240, "SSH in", "note", anchor="middle")
fig.text(200, 276, "52222", "note", anchor="middle")
fig.arrow((tmux.right + 2, 252), (model.x - 2, 252))
fig.text(712, 240, "HTTPS out", "note", anchor="middle")
fig.text(712, 276, "443", "note", anchor="middle")
fig.arrow((bridge.right + 2, 380), (chat.x - 2, 380))
fig.text(712, 368, "polls out", "note", anchor="middle")
fig.arrow((chat.cx, chat.bottom + 2), (phone.cx, phone.bottom + 2), via=[(chat.cx, 476), (phone.cx, 476)])
fig.text(chat.cx - 12, 452, "notify, reply", "note", anchor="end")

fig.caption("The session lives on the server; a client only attaches to it, from wherever the engineer is.")
fig.write()
