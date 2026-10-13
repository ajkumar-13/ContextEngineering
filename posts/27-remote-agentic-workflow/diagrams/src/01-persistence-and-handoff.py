"""Post 27, section 4: one tmux session through a working day, reached from three clients.

Run from the series root:  uv run python posts/27-remote-agentic-workflow/diagrams/src/01-persistence-and-handoff.py
Writes posts/27-remote-agentic-workflow/diagrams/01-persistence-and-handoff.svg.

No numbers and no clock times: the order of events is what the figure shows. The events are sections 4 and 5:
the session is created and attached from the laptop, the laptop closes, the agent blocks and a notification
reaches the phone (the Notification hook), the reply is typed into the session by the bridge (send-keys), the
task completes and notifies (the Stop hook), and a second computer attaches with VS Code. Phrases asserted
against the body. Neutral throughout: no layer of the window is drawn.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("tmux attach -t acme-api", "`Stop` fires when Claude finishes responding",
               "`Notification` fires when Claude Code sends a notification", "tmux send-keys -t acme-api -l",
               "The figure below follows one session through a working day reached from three clients.",
               "the agent cannot tell that the client changed"):
    assert phrase in BODY, phrase

desc = ("A time line from left to right with no clock times. Three client lanes sit above two bars. Laptop: "
        "attached from the start, when it creates the session and starts the task, until the lid closes. Phone: "
        "a notification that the agent is blocked, sent up from the session by the Notification hook, then a "
        "reply sent through the chat bridge, which types it into the session, then a notification that the "
        "task is complete, sent by the Stop hook. Second computer: VS Code attaches "
        "after that and stays attached. Below, the tmux session on the server runs from start to end without a "
        "break, and the agent's task runs inside it from the start until it completes.")
fig = Figure("01-persistence-and-handoff", "One session, three clients, no restart", desc,
             subtitle="A working day on the remote box: clients attach and leave while the tmux session and the "
                      "task run on.",
             data_w=True)

X0, X1 = 232, 920
LANES = {"Laptop": 144, "Phone": 216, "Second computer": 288}   # lane centre lines
for name, cy in LANES.items():
    fig.text(40, cy + 5, name, "label")
    fig.edge((X0, cy), (X1, cy), color="grid", width=0.75)

# laptop: attached, then the lid closes
lap = Box(X0, LANES["Laptop"] - 12, 160, 24)
fig.fill(lap, "neutral-soft", radius=4, fit=False)
fig.outline(lap, "ink-muted", radius=4)
fig.text(lap.x + 8, lap.y + 17, "attached", "label")
fig.text(lap.right + 12, LANES["Laptop"] + 5, "lid closed", "note")

# phone: blocked notification, reply, complete notification
P = LANES["Phone"]
BLOCK, REPLY, DONE = 512, 600, 744
for x in (BLOCK, REPLY, DONE):
    fig.marker(x, P, "diamond", "ink", size=10)
fig.text(BLOCK - 12, P + 5, "Notification hook: blocked", "note", anchor="end")
fig.text(REPLY + 12, P - 12, "reply", "note")
fig.text(DONE + 12, P + 5, "Stop hook: complete", "note")

# second computer: VS Code attaches after the task completes
vs = Box(776, LANES["Second computer"] - 12, X1 - 776, 24)
fig.fill(vs, "neutral-soft", radius=4, fit=False)
fig.outline(vs, "ink-muted", radius=4)
fig.text(vs.x + 8, vs.y + 17, "VS Code", "label")

# the server: the session and the task
SES = Box(X0, 360, X1 - X0, 32)
fig.fill(SES, "neutral-soft", radius=4, fit=False)
fig.outline(SES, "ink", width=1.5, radius=4)
fig.text(40, SES.y + 21, "tmux session", "head")
fig.text(SES.x + 12, SES.y + 21, "on the server, never restarted", "label")
TASK = Box(X0, 416, DONE - X0, 32)
fig.fill(TASK, "surface", radius=4, fit=False)
fig.outline(TASK, "rule", radius=4)
fig.text(40, TASK.y + 21, "Agent task", "head")
fig.text(TASK.x + 12, TASK.y + 21, "running inside the session", "label")
fig.text(TASK.right + 12, TASK.y + 21, "done", "note")

# where a client reaches the session
fig.arrow((lap.x + 64, lap.bottom + 2), (lap.x + 64, SES.y - 2), label="new, attach", side="right")
fig.arrow((REPLY, P + 10), (REPLY, SES.y - 2), label="bridge types it", side="right")
fig.arrow((vs.x + 64, vs.bottom + 2), (vs.x + 64, SES.y - 2), label="attach", side="right")
for x in (BLOCK, DONE):                     # the notifications start on the server
    fig.arrow((x, SES.y - 2), (x, P + 10), width=1)

fig.caption("Only the session has to stay up; any client can come and go.")
fig.write()
