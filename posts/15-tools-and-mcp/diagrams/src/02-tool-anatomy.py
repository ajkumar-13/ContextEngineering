"""Post 15, section 3: the six parts of a tool description, marked on one tool of the post's toy catalogue.

Run from anywhere:  uv run python posts/15-tools-and-mcp/diagrams/src/02-tool-anatomy.py
Writes posts/15-tools-and-mcp/diagrams/02-tool-anatomy.svg.
The tool is search_shipments exactly as snippets/catalogue_budget.py builds it (imported); every value drawn is
read from that dict and the description's three sentences are asserted to be its whole description. The listing
is the JSON the tool serialises to, laid out over several lines for reading (the snippet sends it compact). The
part names are section 3's. No colour carries meaning: the listing and the markers are neutral.
"""
import json
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, text_width  # noqa: E402

POST = Path(__file__).resolve().parents[2]
SNIP = runpy.run_path(str(POST / "snippets" / "catalogue_budget.py"), run_name="figure")
TOOL = next(t for t in SNIP["CATALOGUE"] if t["name"] == "search_shipments")
BODY = (POST / "index.md").read_text(encoding="utf-8")

s1, s2, s3 = [s if s.endswith(".") else s + "." for s in TOOL["description"].split(". ")]
assert f"{s1[:-1]}. {s2[:-1]}. {s3}" == TOOL["description"]
assert f'*"{s2}"*' in BODY and f'*"{s3}"*' in BODY, "section 3 quotes sentences 3 and 4 of this tool"
props = TOOL["input_schema"]["properties"]
assert list(props) == ["email", "since", "status"] and TOOL["input_schema"]["required"] == []
assert TOOL["input_schema"]["additionalProperties"] is False and len(TOOL["input_examples"]) == 1
for part in ("1. **Name.**", "2. **One-line summary.**", "3. **When to use it.**", "4. **When not to use it.**",
             "5. **Parameters.**", "6. **One worked example.**"):
    assert part in BODY, part

j = lambda v: json.dumps(v)  # noqa: E731
p = {k: v for k, v in props.items()}
st = p["status"]
LINES = [  # (marker or None, line)
    (None, "{"),
    (1, f'  "name": {j(TOOL["name"])},'),
    (None, '  "description":'),
    (2, f'    "{s1}'),
    (3, f'     {s2}'),
    (4, f'     {s3}",'),
    (None, '  "input_schema": {'),
    (None, '    "type": "object",'),
    (5, '    "properties": {'),
    (None, f'      "email": {{"type": {j(p["email"]["type"])}, "description": {j(p["email"]["description"])}}},'),
    (None, f'      "since": {{"type": {j(p["since"]["type"])}, "description": {j(p["since"]["description"])}}},'),
    (None, f'      "status": {{"type": {j(st["type"])},'),
    (None, f'                 "enum": {j(st["enum"])},'),
    (None, f'                 "description": {j(st["description"])}}}'),
    (None, '    },'),
    (None, '    "required": [],'),
    (None, '    "additionalProperties": false'),
    (None, '  },'),
    (6, '  "input_examples": ['),
    (None, f'    {j(TOOL["input_examples"][0])}'),
    (None, '  ]'),
    (None, "}"),
]
NAMES = {1: "name", 2: "summary", 3: "when to use", 4: "when not to", 5: "parameters", 6: "example"}

desc = (f"The JSON definition of the tool {TOOL['name']} from the post's toy catalogue, with six numbered markers in "
        f"the left margin. 1, name: {TOOL['name']}. 2, summary: {s1} 3, when to use: {s2} 4, when not to: {s3} "
        f"5, parameters: email and since as strings with descriptions, and status as an enum of "
        f"{', '.join(st['enum'])}, with additionalProperties false. 6, example: an input_examples entry with "
        f"an email, a start date and the status delivered.")
fig = Figure("02-tool-anatomy", "Six parts of one tool description", desc,
             subtitle="search_shipments as the post's snippet builds it; the model reads every line on every call.",
             height=720, data_w=True)

X_NUM, X_NAME, X_CODE, Y0, LEAD = 56, 76, 184, 128, 24
spaces = lambda s: len(s) - len(s.lstrip(" "))  # noqa: E731
SP = text_width("x" * 10, 14, mono=True) / 10   # one mono character
for i, (mark, line) in enumerate(LINES):
    y = Y0 + i * LEAD
    x = X_CODE + spaces(line) * SP
    fig.text(x, y, line.lstrip(" "), "code", _attrs=' xml:space="preserve"') if "  " in line.strip() else \
        fig.text(x, y, line.lstrip(" "), "code")
    if mark:
        fig.node(X_NUM, y - 5, r=12, label=str(mark))
        fig.text(X_NAME, y, NAMES[mark], "note")

# brackets for the parts that span several lines: 5 the parameters, 6 the example
first = {m: i for i, (m, _) in enumerate(LINES) if m}
spans = {5: (first[5], [i for i, (_, l) in enumerate(LINES) if '"additionalProperties"' in l][0]),
         6: (first[6], len(LINES) - 2)}
for m, (i0, i1) in spans.items():
    fig.brace(Y0 + i0 * LEAD - 16, Y0 + i1 * LEAD + 6, X_CODE - 16, side="left", kind="bracket", vertical=True)

fig.caption("Parts 2 to 4 are sentences of one description; part 5 is the schema; part 6 an example.")
fig.write()
