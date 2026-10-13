"""Image tokens, screenshots, pages and audio, counted with the providers' published rules.

Run from the series root:  uv run python posts/19-multimodal-context/snippets/image_tokens.py
Standard library only; no network call, no API key.

Sources, consulted October 2026:
  Anthropic, "Vision": an image costs one visual token per 28 x 28 pixel patch, ceil(w/28) x ceil(h/28);
    the standard tier (1568 px long edge, 1568 tokens) and the high-resolution tier of Claude 4.7 and later
    (2576 px, 4784 tokens); the example sizes in VISION_TABLE.
  Anthropic, "Coordinates and bounding boxes": the resize rule (the largest aspect-preserving size within
    both limits) and its A4 example, 1075 x 1520 pixels resized to 924 x 1307.
  Anthropic, "Computer use tool": 1280 x 800 is one of the screenshot sizes it recommends.
  Google, "Audio understanding" (Gemini API): 32 tokens per second of audio.
Every page count, word count, session length and call length below is illustrative.
"""
import math

PATCH = 28                                             # pixels per side of one visual token
TIERS = {"standard": (1568, 1568), "high-res": (2576, 4784)}   # (max long edge, max visual tokens)


def visual_tokens(width, height):
    """One visual token per 28 x 28 patch, rounding each side up."""
    return math.ceil(width / PATCH) * math.ceil(height / PATCH)


def fits(width, height, max_edge, max_tokens):
    return (math.ceil(width / PATCH) * PATCH <= max_edge
            and math.ceil(height / PATCH) * PATCH <= max_edge
            and visual_tokens(width, height) <= max_tokens)


def resized(width, height, tier="standard"):
    """The size an image is downscaled to before it is read: unchanged if it fits both limits."""
    max_edge, max_tokens = TIERS[tier]
    if fits(width, height, max_edge, max_tokens):
        return width, height
    if height > width:
        h, w = resized(height, width, tier)
        return w, h
    aspect = width / height
    lo, hi = 1, width                  # binary search on the long edge: lo always fits, hi never does
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if fits(mid, max(round(mid / aspect), 1), max_edge, max_tokens):
            lo = mid
        else:
            hi = mid
    return lo, max(round(lo / aspect), 1)


def image_tokens(width, height, tier="standard"):
    return visual_tokens(*resized(width, height, tier))


def a4(dpi):
    """Pixel size of an A4 page (210 x 297 mm) rendered at a given resolution."""
    return round(210 / 25.4 * dpi), round(297 / 25.4 * dpi)


# The "Vision" page's table: (width, height) -> (standard-tier tokens, high-resolution-tier tokens)
VISION_TABLE = {(200, 200): (64, 64), (1000, 1000): (1296, 1296), (1092, 1092): (1521, 1521),
                (1920, 1080): (1560, 2691), (2000, 1500): (1564, 3888), (3840, 2160): (1560, 4784)}
for (w, h), tokens in VISION_TABLE.items():
    assert (image_tokens(w, h), image_tokens(w, h, "high-res")) == tokens, (w, h)
assert resized(1075, 1520) == (924, 1307)
print(f"rule check: the {len(VISION_TABLE)} sizes of the Vision page and its A4 example reproduce")

print("\none A4 page sent as an image")
for dpi in (72, 130, 300):
    w, h = a4(dpi)
    cells = []
    for tier in TIERS:
        rw, rh = resized(w, h, tier)
        cells.append(f"{tier} {rw}x{rh} = {visual_tokens(rw, rh)} tokens")
    print(f"  {dpi:3d} dpi, {w}x{h}: " + "; ".join(cells))

PAGE = image_tokens(*a4(130))
INPUT_RATE = 5.0                       # Claude Opus 4.6, dollars per million input tokens, as of early 2026
print(f"1000 pages at 130 dpi on Claude Opus 4.6: {1000 * PAGE} tokens, "
      f"{1000 * PAGE * INPUT_RATE / 1e6:.3f} dollars of input")

SHOT, TURNS, KEEP = (1280, 800), 20, 3
per_shot = image_tokens(*SHOT)
print(f"\nscreenshot {SHOT[0]}x{SHOT[1]}: {per_shot} tokens; after {TURNS} turns, "
      f"all kept {TURNS * per_shot}, last {KEEP} kept {KEEP * per_shot}")

WORDS_PER_PAGE = 600                   # a full page of prose
TEXT_PAGE = round(WORDS_PER_PAGE / 0.75)   # post 04's rule: a token is about three quarters of a word


def route(page):
    """Pixels when there is no text layer or the layout carries meaning; extracted text otherwise."""
    return "pixels" if not page["text_layer"] or page["layout_matters"] else "text"


FILING = [{"kind": "prose", "text_layer": True, "layout_matters": False}] * 40 \
    + [{"kind": "table", "text_layer": True, "layout_matters": True}] * 10
cost = {"text": TEXT_PAGE, "pixels": PAGE}
per_page = sum(cost[route(p)] for p in FILING)
print(f"\npage as text {TEXT_PAGE} tokens, as pixels {PAGE} tokens")
print(f"50-page filing (40 prose, 10 tables): all text {len(FILING) * TEXT_PAGE}, "
      f"all pixels {len(FILING) * PAGE}, routed per page {per_page}, "
      f"text and image of every page {len(FILING) * (TEXT_PAGE + PAGE)}")
print(f"scanned invoice, no text layer: {route({'text_layer': False, 'layout_matters': False})}")

MINUTES, AUDIO_PER_SECOND, WORDS_PER_MINUTE = 30, 32, 150
print(f"\n{MINUTES}-minute call: native audio {MINUTES * 60 * AUDIO_PER_SECOND} tokens, "
      f"transcript {round(MINUTES * WORDS_PER_MINUTE / 0.75)} tokens")
