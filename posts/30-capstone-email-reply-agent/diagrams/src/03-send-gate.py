"""Post 30, figure 3 (section 9): the companion's three send-gate checks, and nine drafts through them.

Run from the series root:  uv run python posts/30-capstone-email-reply-agent/diagrams/src/03-send-gate.py
Writes posts/30-capstone-email-reply-agent/diagrams/03-send-gate.svg.
Every verdict is computed here: the script imports the post's snippet snippets/send_gate_cases.py, which loads
the companion's send_gate.py, and calls the gate on the snippet's nine cases; the verdicts and the gate's hours
are asserted against the printed table that section 9 of index.md quotes. A harmful draft the gate passes is
drawn in the error colour (ctx_fig_design.md Section 0: red is a failure, never a layer).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
POST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(POST / "snippets"))
from figkit import Box, Figure, rich, span  # noqa: E402
import send_gate_cases as sg  # noqa: E402

BODY = (POST / "index.md").read_text(encoding="utf-8")
assert (sg.gate.BUSINESS_START_H, sg.gate.BUSINESS_END_H) == (9, 18)
assert "gate hours: 09:00 to 18:00; thread A is t-001" in BODY

SHORT = {  # what each draft adds, in a few words (the full drafts are in the snippet)
    "1 clean reply": "14:00 IST", "2 new link": "a docs.example link", "3 new money term": "a $5,000 fee",
    "4 late hour": "21:30 IST", "5 hour without colon": "9 pm IST", "6 money in words": "five thousand dollars",
    "7 runs past 18:00": "17:45 IST, 30 min", "8 bigger sum": "$50,000 after $500", "9 injected link": "the email's own link"}
rows, outcomes = [["Draft", "It adds", "Gate", "Outcome"]], {}
for case, thread, body, should_block in sg.CASES:
    d = sg.gate.send_gate(body, thread, known_urls=sg.KNOWN_URLS)
    outcome = "right" if d.ok != should_block else ("missed" if should_block else "false block")
    says = "ok" if d.ok else f"BLOCK {d.reason}"
    assert any(line.startswith(case) and says in line and line.rstrip().endswith(outcome)
               for line in BODY.splitlines()), case
    outcomes[case] = outcome
    check = {"unknown_url": 1, "introduced_monetary_term": 2, "non_business_hour": 3}
    gate_word = "passes" if d.ok else f"blocks at {check[d.reason.split(':')[0]]}"
    rows.append([case[2:], SHORT[case], gate_word,
                 rich(span(outcome, color="error")) if outcome != "right" else outcome])
assert list(outcomes.values()).count("missed") == 4 and "false block" not in outcomes.values()

desc = ("Left, the companion's three checks in order: a URL allow-list of the operator's known_urls only; no "
        "money term (a currency sign or code with digits) unless the thread has one; times written as hours and minutes "
        "from 09:00 to before 18:00. Right, nine drafts from the post's snippet. The gate passes the clean reply "
        "at 14:00 IST and blocks a new docs.example link, a new $5,000 fee, 21:30 IST and the injected email's "
        "own link, all right. It passes 9 pm IST, five thousand dollars, a 30-minute call at 17:45 IST and "
        "$50,000 in a thread that mentions $500, four harmful drafts marked missed in red.")
fig = Figure("03-send-gate", "Three patterns block what they match, and only that", desc,
             subtitle="The companion's send_gate on nine drafts from the post's snippet; red: a harmful draft it passes.",
             height=720, data_w=True)

CHECKS = [("1. URL allow-list", ["the operator's list", "(known_urls) only"]),
          ("2. No new money", ["a currency sign or code", "with digits, not in the thread"]),
          ("3. Business hours", ["HH:MM from 09:00", "to before 18:00"])]
cards = []
for k, (h, lines) in enumerate(CHECKS):
    b = Box(40, 136 + 152 * k, 240, 120)
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    fig.outline(b, "ink-muted", width=1.5, radius=8)
    fig.text(b.x + 16, b.y + 32, h, "head")
    for i, s in enumerate(lines):
        fig.text(b.x + 16, b.y + 64 + 24 * i, s, "label")
    cards.append(b)
fig.text(40, 120, "The gate, in order", "head")
fig.chain(cards)
fig.text(40, cards[-1].bottom + 32, "first failing check blocks", "note")

fig.table(328, 120, rows, [176, 192, 120, 104], row_h=48)
fig.caption("Every miss is a gap in a pattern; the review in front of the gate has to catch them.")
fig.write()
