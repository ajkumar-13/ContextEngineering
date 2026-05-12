# Contributing

Contributions are welcome. This guide covers style, diagram standards,
and the PR process.

---

## TL;DR

- One topic per PR; small is better than complete.
- Match the **voice** template at the top of every post.
- Match the **design tokens** for any new diagram.
- Cite every non-obvious claim; no hand-waved numbers.
- Run the linters and the word-count script before submitting.

---

## Voice

Every post uses the same shape. Keep it.

**Top of post:**

```markdown
> **TL;DR.** Two-sentence summary.
>
> **Reading time:** ~N minutes.
>
> **After reading this you will be able to:**
> - Three concrete capabilities. Each starts with a verb.
> - …
> - …
```

Then a hero diagram (SVG embedded inline if small; image link if large).

**Body:** numbered sections (`## 1. …`, `## 2. …`). Third-person textbook
voice. No "we", no "you", no marketing tone. Concrete numbers and
citations beat assertions.

**Bottom of post:**

```markdown
## Common pitfalls
- Bullets, 4–7 of them, of mistakes the reader will actually make.

## Further reading
- Citations. Author, "Title", year.

Full citations in REFERENCES.md.

## What to read next
- Forward and sideways links.
```

Reading time targets 10–14 minutes for principles posts, 12–14 for the
build posts.

---

## Design tokens (locked)

Use these for **every** new diagram. Variants are fine; departures are not.

**Light palette**

| Token | Value | Use |
|---|---|---|
| `--ce-bg` | `#FAFAF7` | page background |
| `--ce-surface` | `#FFFFFF` | cards, boxes |
| `--ce-ink` | `#1A1A1A` | text, primary strokes |
| `--ce-primary` | `#5B7FBF` | primary fills, links |
| `--ce-accent` | `#D98E5F` | secondary fills |
| `--ce-success` | `#5C9E78` | "good" outcomes |
| `--ce-warn` | `#B8895A` | "caution" |
| `--ce-alert` | `#C66B5E` | "bad" outcomes |

**Dark palette** (for `prefers-color-scheme: dark`)

`#8BA8E0` / `#E8B088` / `#7FBF9B` / `#D4B58A` / `#D88880`.

**Typography**

- Inter for labels.
- JetBrains Mono for code and monospace labels.

**Strokes**

- 1.5 for primary; 1.0 for secondary; 0.75 for grids.

**SVG hygiene**

- Self-contained: every SVG inlines its own `:root` variables and a
  `@media (prefers-color-scheme: dark)` block. No external CSS.
- `viewBox` set; no fixed `width`/`height` attributes.
- Text uses `<text>` elements with the typography above; never images of text.

See `templates/diagram-style-guide.md` for the full spec.

---

## Citations

Every non-obvious claim cites a primary source: a paper, a vendor doc, a
talk, or an empirical post. Citation style:

> Liu et al., *"Lost in the Middle: How Language Models Use Long Contexts"*
> (2023).

Inline: `(Liu et al., 2023)`. Full bibliography lives in `REFERENCES.md`;
each post's "Further reading" section names its sources and points there.

If a number is in the post (a percentage, a token count, a benchmark
score), the source must appear in the post's Further reading. No invented
numbers.

---

## Code

- Python 3.11+ for new code.
- Direct provider SDKs first (`openai`, `anthropic`, `voyageai`, `cohere`).
  A framework appears only when it materially changes the shape.
- One `pyproject.toml` per `code/<post>/` directory.
- A `README.md` per code directory with quickstart + what's stubbed.
- Tests under `tests/` with pytest. Aim for the safety surface, not coverage.

---

## Tools

The `tools/` directory has small PowerShell scripts:

- `tools/word-count.ps1` — reading-time check per post.
- `tools/lint-posts.ps1` — voice-template structural check.
- `tools/render-diagrams.ps1` — re-export Mermaid / Excalidraw sources.
- `tools/build-cheatsheet.ps1` — assemble the printable cheatsheet.

Run them before submitting:

```powershell
pwsh tools/word-count.ps1
pwsh tools/lint-posts.ps1
```

---

## PR process

1. Open an issue first for anything beyond a typo.
2. Branch from `main`; one topic per PR.
3. CI runs the linters and (when present) the eval harnesses for code
   directories. A regression on any tracked metric blocks merge.
4. The author of the series reviews. Two business-day turnaround for
   typo / clarity PRs; longer for new posts or new diagrams.

---

## Code of conduct

Be kind. Disagree on ideas; never on people.
