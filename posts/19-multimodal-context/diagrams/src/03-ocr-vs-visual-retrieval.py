"""Post 19, section 4: two ways to retrieve over page images, and what the ColPali paper reports for each.

Run from the series root:  uv run python posts/19-multimodal-context/diagrams/src/03-ocr-vs-visual-retrieval.py
Writes posts/19-multimodal-context/diagrams/03-ocr-vs-visual-retrieval.svg.

The two routes are section 4's. The numbers are cited, from Faysse et al., "ColPali: Efficient Document
Retrieval with Vision Language Models" (arXiv:2407.01449v6, ICLR 2025), listed in CITED and asserted against the
values section 4 states: Table 2 (average nDCG@5 over the ten ViDoRe tasks) and Table 4 (embedding size per page
on the DocVQA set of ViDoRe).
"""
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

CITED = {  # value: (number, where in the paper)
    "nDCG@5, Unstructured + OCR + BM25": (65.5, "Table 2, Avg."),
    "nDCG@5, Unstructured + OCR + BGE-M3": (66.1, "Table 2, Avg."),
    "nDCG@5, Unstructured + Captioning + BGE-M3": (67.0, "Table 2, Avg., the best text pipeline"),
    "nDCG@5, ColPali": (81.3, "Table 2, Avg."),
    "KB per page, BGE-M3": (8.60, "Table 4"),
    "KB per page, ColPali (float16)": (257.5, "Table 4"),
}
# the ten per-task values of Table 2 average to the reported means
OCR_BM25 = [31.6, 36.8, 62.9, 46.5, 62.7, 64.3, 92.8, 85.9, 83.9, 87.2]
COLPALI = [79.1, 54.4, 81.8, 83.9, 65.8, 73.2, 96.2, 91.0, 92.7, 94.4]
assert abs(sum(OCR_BM25) / 10 - CITED["nDCG@5, Unstructured + OCR + BM25"][0]) <= 0.05 + 1e-9
assert abs(sum(COLPALI) / 10 - CITED["nDCG@5, ColPali"][0]) <= 0.05 + 1e-9
OCR = CITED["nDCG@5, Unstructured + OCR + BGE-M3"][0]
COL = CITED["nDCG@5, ColPali"][0]
KB_TEXT, KB_COL = CITED["KB per page, BGE-M3"][0], CITED["KB per page, ColPali (float16)"][0]
assert (OCR, COL, KB_TEXT, KB_COL) == (66.1, 81.3, 8.60, 257.5)

fig = Figure(
    "03-ocr-vs-visual-retrieval", "OCR first, or retrieve on the pixels",
    "Two pipelines from left to right. OCR then text RAG: page image, OCR and parse (where layout and charts are lost and misread "
    "characters enter, marked in red), chunk the text, embed one vector per chunk and score, top-k "
    "chunks into layer 04. Visual retrieval with ColPali: page image, embed the patches with one vector per "
    "patch and no OCR, score with MaxSim between query tokens and patches, top-k pages into layer 04. A table of "
    "cited values from the ColPali paper: average nDCG@5 on ViDoRe is 66.1 for OCR text with BGE-M3 and 81.3 "
    "for ColPali; an embedding takes 8.60 KB a vector with BGE-M3 and 257.5 KB a page with ColPali.",
    subtitle="Values cited from Faysse et al., ColPali (ICLR 2025), Tables 2 and 4.",
    height=720, data_w=True)

X = [40 + k * 180 for k in range(5)]
CW, CH = 160, 88


def lane(y, heading, cards):
    fig.text(40, y - 16, heading, "head")
    boxes = []
    for col, span, head, line, role in cards:
        w = CW + (span - 1) * 180
        fig.card(X[col], y, w, CH, heading=head, lines=[line], style="note", color=role)
        boxes.append(Box(X[col], y, w, CH))
    fig.chain(boxes)
    return boxes


l1 = lane(152, "OCR, then text RAG", [
    (0, 1, "Page image", "pixels", None),
    (1, 1, "OCR and parse", "text only", None),
    (2, 1, "Chunk", "text chunks", None),
    (3, 1, "Embed, score", "one vector a chunk", None),
    (4, 1, "Top-k chunks", "into layer 04", "turn"),
])
fig.note(l1[1], ["layout and charts are lost,", "misread characters enter"], color="error-ink")

l2 = lane(360, "Visual retrieval (ColPali)", [
    (0, 1, "Page image", "pixels", None),
    (1, 2, "Embed the patches", "one vector a patch, no OCR", None),
    (3, 1, "MaxSim", "query tokens, patches", None),
    (4, 1, "Top-k pages", "into layer 04", "turn"),
])

fig.text(40, 504, "Cited from the paper", "head")
fig.table(40, 520, [["Route", "nDCG@5, average on ViDoRe", "Embedding size"],
                    ["OCR text, BGE-M3 embeddings", f"{OCR}", f"{KB_TEXT:.2f} KB a vector"],
                    ["ColPali, patch vectors", f"{COL}", f"{KB_COL} KB a page"]],
          [320, 240, 200], col_align=["start", "end", "end"])

fig.caption("The visual route keeps the layout that OCR drops, and pays for it in index size.")
fig.write()
