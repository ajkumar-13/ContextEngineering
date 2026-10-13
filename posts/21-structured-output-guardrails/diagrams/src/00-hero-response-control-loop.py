"""Post 21, hero (sections 5 and 6): the response control loop, validate and retry with a cap, then guard.

Run from anywhere:  uv run python posts/21-structured-output-guardrails/diagrams/src/00-hero-response-control-loop.py
Writes posts/21-structured-output-guardrails/diagrams/00-hero-response-control-loop.svg.
The loop is snippets/validate_retry.py's parse_with_retry (imported): the cap of 3 attempts is read from its
default and the three ways out of the loop (Refused, CutOff, Exhausted) are asserted to exist. The guardrail
checks and their decisions are those snippets/output_guard.py prints (run and parsed). No colour marks a layer:
the boxes are neutral, and red marks the paths on which no record is delivered.
"""
import contextlib
import inspect
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
VR = runpy.run_path(str(POST / "snippets" / "validate_retry.py"), run_name="figure")
CAP = inspect.signature(VR["parse_with_retry"]).parameters["max_attempts"].default
assert CAP == 3 and all(k in VR for k in ("Refused", "CutOff", "Exhausted"))
assert "after three attempts (a common ceiling, illustrative)" in BODY
out = io.StringIO()
with contextlib.redirect_stdout(out):
    runpy.run_path(str(POST / "snippets" / "output_guard.py"), run_name="__main__")
decisions = [line.split()[0] for line in out.getvalue().splitlines()[1:] if not line.startswith(" ")]
assert decisions == ["pass", "fix", "fix", "block", "block", "fallback"], decisions
for reason in ("moderation flagged the reply", "the reply leaks system detail", "redacted a card number"):
    assert reason in out.getvalue()

desc = (f"A chain of four boxes. The model returns a reply and a stop reason; parse and validate checks it "
        f"against the JSON Schema and the rules; output guardrails run moderation, a leak check and PII "
        f"redaction; the reply is sent as is (pass) or redacted (fix). An arrow from validate back to the model "
        f"carries an invalid reply with its error appended, at most {CAP} attempts. Below validate, a red box: "
        f"the reply leaves the loop on a refusal (fallback message), a cut-off at max_tokens (raise max_tokens) "
        f"or {CAP} failed attempts (counted). Below the guardrails, a red box: a reply flagged by moderation or "
        f"the leak check is blocked and the draft goes to a human.")
fig = Figure("00-hero-response-control-loop", "Validate, retry with a cap, then guard", desc,
             subtitle="The loop of snippets/validate_retry.py, then the checks of snippets/output_guard.py.",
             data_w=True)

TOP, H = 168, 136
model = Box(40, TOP, 136, H)
valid = Box(232, TOP, 200, H)
guard = Box(488, TOP, 200, H)
sent = Box(744, TOP, 176, H)
fig.card(model.x, model.y, model.w, model.h, heading="Model", lines=["reply and", "stop reason"])
fig.card(valid.x, valid.y, valid.w, valid.h, heading="Parse and validate", lines=["JSON Schema", "and the rules"])
fig.card(guard.x, guard.y, guard.w, guard.h, heading="Output guardrails",
         lines=["moderation", "leak check", "PII redaction"])
fig.card(sent.x, sent.y, sent.w, sent.h, heading="Sent", lines=["pass: as is", "fix: redacted"])
fig.arrow(model.anchor("right"), valid.anchor("left"), label="reply")
fig.arrow(valid.anchor("right"), guard.anchor("left"), label="record")
fig.arrow(guard.anchor("right"), sent.anchor("left"))

# the retry loop, over the top of the row
fig.arrow(valid.anchor("top"), model.anchor("top"), via=[(valid.cx, 136), (model.cx, 136)])
fig.text(model.cx + 16, 128, f"invalid: the reply and its error go back, at most {CAP} attempts", "note")

# the ways out, under the row
leave = Box(208, 352, 248, 128)
fig.card(leave.x, leave.y, leave.w, leave.h, heading="Leaves the loop", color="error",
         lines=["refusal: fallback message", "cut off: raise max_tokens", f"{CAP} failed attempts: counted"])
fig.arrow(valid.anchor("bottom"), (valid.cx, leave.y))
block = Box(488, 352, 200, 104)
fig.card(block.x, block.y, block.w, block.h, heading="Blocked", color="error",
         lines=["moderation or leak", "draft goes to a human"])
fig.arrow(guard.anchor("bottom"), (guard.cx, block.y))

fig.caption("A retry repairs what rewording can fix; a refusal, a cut-off or a block leaves by another path.")
fig.write()
