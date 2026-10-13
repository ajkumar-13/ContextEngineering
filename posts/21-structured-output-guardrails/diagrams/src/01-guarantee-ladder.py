"""Post 21, section 2: the ladder of output guarantees, four rungs and what each leaves to the application.

Run from anywhere:  uv run python posts/21-structured-output-guardrails/diagrams/src/01-guarantee-ladder.py
Writes posts/21-structured-output-guardrails/diagrams/01-guarantee-ladder.svg.
The rungs and what each guarantees are section 2's, as it cites them: OpenAI's "Structured Outputs" and
"Function calling" guides and Anthropic's "Structured outputs" page, consulted October 2026. The phrases drawn
are asserted against the body. A table, as ctx_fig_design.md Section 4 asks for a comparison; no colour carries
meaning (no rung is a layer), and request fields are drawn in the code face.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, text_width  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("**A prompt instruction.**", "**JSON mode.**", '`response_format: {"type": "json_object"}`',
               "**A schema without strict mode.**", "instead of being best effort",
               "**A strict schema, enforced by constrained decoding.**", "`output_config.format`",
               "`strict: true`", "only Structured Outputs ensure schema adherence"):
    assert phrase in BODY, phrase

# rung, request (code face or None), request in prose (or None), guarantees, leaves to the application
ROWS = [
    ("Strict schema", "strict: true", None, "the shape", "meaning, refusals, cut-offs, dropped keywords"),
    ("Schema, not strict", None, "a schema, best effort", "nothing hard", "shape and meaning"),
    ("JSON mode", '{"type": "json_object"}', None, "valid JSON", "shape and meaning"),
    ("Prompt instruction", None, "\u201cReply in JSON.\u201d", "nothing", "syntax, shape and meaning"),
]

desc = ("A table of four rungs of output guarantee, strongest at the top. Strict schema, asked with strict: true "
        "(or output_config.format): guarantees the shape and leaves meaning, refusals, cut-offs and dropped "
        "keywords. Schema, not strict, a schema followed on a best-effort basis: guarantees nothing hard and leaves "
        "shape and meaning. JSON mode, response_format type json_object: guarantees valid JSON and leaves shape "
        "and meaning. Prompt instruction, reply in JSON: guarantees nothing and leaves syntax, shape and meaning.")
fig = Figure("01-guarantee-ladder", "Four rungs, and what each leaves to the application", desc,
             subtitle="Strongest at the top; as OpenAI's and Anthropic's structured-output pages state it, October 2026.",
             data_w=True)

X, Y, RH = 40, 136, 64
W = [200, 232, 136, 312]
assert X + sum(W) == 920
rows = [["Rung", "Asked with", "Guarantees", "Leaves to the application"]]
rows += [[r, prose or "", g, left] for r, code, prose, g, left in ROWS]
fig.table(X, Y, rows, W, row_h=RH, col_align=["start", "start", "start", "start"])
for i, (_, code, _, _, _) in enumerate(ROWS, start=1):
    if code:
        fig.text(X + W[0] + 8, Y + i * RH + 36, code, "code")
or_x = X + W[0] + 8 + text_width("strict: true", 14, mono=True) + 8
fig.text(or_x - or_x % 4 + 4, Y + RH + 36, "or", "note")
fig.text(X + W[0] + 8, Y + RH + 56, "output_config.format", "code")

fig.caption("Each rung removes a class of failure; none of them removes the validator.")
fig.write()
