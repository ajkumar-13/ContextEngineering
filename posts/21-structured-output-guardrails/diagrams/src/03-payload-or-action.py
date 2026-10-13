"""Post 21, section 4: a structured response format or a tool call, by whether the answer is the payload.

Run from anywhere:  uv run python posts/21-structured-output-guardrails/diagrams/src/03-payload-or-action.py
Writes posts/21-structured-output-guardrails/diagrams/03-payload-or-action.svg.
Field names and tool_choice settings are section 4's, as it cites OpenAI's "Structured Outputs" and "Function
calling" guides and Anthropic's "Define tools" page (consulted October 2026); each is asserted against the body.
Two neutral cards side by side, as ctx_fig_design.md Section 4 asks for a comparison; names in the code face.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
FIELDS = [("Chat Completions", "response_format"), ("Responses", "text.format"),
          ("Anthropic Messages", "output_config.format")]
SETTINGS = [("auto", "auto", "may call none"), ("required", "any", "must call one"),
            (None, "tool", "must call that one"), ("none", "none", "calls nothing")]
assert ("`response_format` in OpenAI's Chat Completions, `text.format` in its Responses API and "
        "`output_config.format` in Anthropic's Messages API") in BODY
assert all(f"`{s}`" in BODY for s in ("auto", "required", "none", "any", "tool"))
assert "a forced function" in BODY and "`tool` (one named tool)" in BODY

desc = ("Two cards. Left, structured response format: the answer is the payload, one shape every time, such as a "
        "label, an extraction, a form or a grade; the field is response_format in Chat Completions, text.format in "
        "Responses and output_config.format in Anthropic Messages. Right, tools steered by tool_choice: the model "
        "chooses an action among several, or none. OpenAI auto and Anthropic auto: may call none; required and any: "
        "must call one; a named function and tool: must call that one; none and none: calls nothing.")
fig = Figure("03-payload-or-action", "Is the answer the payload, or an action?", desc,
             subtitle="Fields and settings as OpenAI's and Anthropic's pages give them, consulted October 2026.",
             data_w=True)

Y, H, CW = 120, 344, 424
L, R = 40, 496
fig.card(L, Y, CW, H, heading="Structured response format",
         lines=["The answer is the payload: one shape,", "every time. A label, an extraction, a form."])
fig.card(R, Y, CW, H, heading="Tools, steered by tool_choice",
         lines=["The model chooses an action,", "among several, or none."])

TY, RH = 232, 40
fig.table(L + 16, TY, [["API", "Field"]] + [[api, ""] for api, _ in FIELDS], [168, 224], row_h=RH)
for i, (_, field) in enumerate(FIELDS, start=1):
    fig.text(L + 16 + 168 + 8, TY + i * RH + 24, field, "code")
fig.table(R + 16, TY, [["OpenAI", "Anthropic", "The model"]] + [["" if o else "a named function", "", m]
                                                              for o, _, m in SETTINGS],
          [136, 104, 152], row_h=RH)
for i, (o, a, _) in enumerate(SETTINGS, start=1):
    if o:
        fig.text(R + 16 + 8, TY + i * RH + 24, o, "code")
    fig.text(R + 16 + 136 + 8, TY + i * RH + 24, a, "code")

fig.caption("A menu, and the option to call nothing, is the whole test.")
fig.write()
