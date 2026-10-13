"""Post 27, section 7: every control on a remote agent box, and what enforces it outside the prompt.

Run from the series root:  uv run python posts/27-remote-agentic-workflow/diagrams/src/03-remote-controls.py
Writes posts/27-remote-agentic-workflow/diagrams/03-remote-controls.svg.

No numbers. The seven rows are the controls of sections 3 and 7 (security group, key-only SSH with MFA or EC2
Instance Connect, the instance role, the hook deny-list, read-only mounts, staging-only credentials, the audit
log); the phrases are asserted against the body. A table, as ctx_fig_design.md Section 4 draws grids: words, no
glyphs, neutral.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("**security group** is the instance's virtual firewall", "EC2 Instance Connect", "**MFA on SSH**",
               "**IAM instance role**", "**A deny-list of dangerous commands at the hook level**",
               "**Read-only mounts**", "**No production credentials on the development box.**",
               "**An audit log**", "the table below lists every control in one place"):
    assert phrase in BODY, phrase

ROWS = [
    ["What is fenced", "The control", "Enforced by"],
    ["Who can reach the box", "security group: SSH from a known range", "the cloud network"],
    ["How a person logs in", "keys only, MFA, or Instance Connect", "sshd and IAM"],
    ["Which cloud APIs it may call", "a scoped instance role", "IAM"],
    ["What the agent may run", "a deny-list hook", "the host, before the tool"],
    ["What it may write", "read-only mounts", "the filesystem"],
    ["What it can deploy", "staging credentials only", "the CI/CD pipeline"],
    ["What it did", "an audit log of every command", "logging the agent cannot edit"],
]
desc = ("A table of seven rows and three columns: what is fenced, the control, and what enforces it. Who can "
        "reach the box: a security group allowing SSH from a known range, enforced by the cloud network. How a "
        "person logs in: keys only, MFA, or EC2 Instance Connect, enforced by sshd and IAM. Which cloud APIs "
        "it may call: a scoped instance role, enforced by IAM. What the agent may run: a deny-list hook, enforced by "
        "the host before the tool runs. What it may write: read-only mounts, enforced by the filesystem. What it "
        "can deploy: staging credentials only, enforced by the CI/CD pipeline. What it did: an audit log of every "
        "command, kept by logging the agent cannot edit.")
fig = Figure("03-remote-controls", "Every control on the box sits outside the prompt", desc,
             subtitle="What is fenced on a remote agent box, the control that fences it, and what enforces it.",
             data_w=True)
fig.table(40, 120, ROWS, [240, 336, 304], row_h=44)
fig.caption("Nothing the model reads can switch off a control that lives in the network, IAM or the filesystem.")
fig.write()
