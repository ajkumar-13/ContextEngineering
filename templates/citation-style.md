# Citation style

Every non-obvious claim in this series cites a primary source. The format
is consistent across posts so a reader can scan a "Further reading"
section and recognise the shape immediately.

---

## In-prose

When a claim is attributed mid-sentence, use the parenthetical short form:

> Models exhibit a U-shaped attention pattern across long contexts
> (Liu et al., 2023).

When the source title matters, name it inline in italics:

> Anthropic's *"Contextual retrieval"* technique reduces retrieval failures
> by ~35 % (Anthropic Engineering, 2024).

## Further reading bullets

End-of-post bullets use this shape, alphabetised by surname / org:

```markdown
## Further reading

- Anthropic Engineering, *"Contextual retrieval"* (2024).
- Liu, N. F., et al., *"Lost in the Middle: How Language Models Use Long
  Contexts"* (TACL, 2024).
- modelcontextprotocol.io, *"Specification"* (latest).
- Schick, T., et al., *"Toolformer: Language Models Can Teach Themselves
  to Use Tools"* (NeurIPS, 2023).
```

Rules:

- **Author / org first.** Multi-author papers use the first author plus "et al.".
- **Title in italics, in quotes** for short works (papers, blog posts);
  italics without quotes for books.
- **Venue + year** in parentheses for academic; year alone for blog posts
  and docs; "(latest)" for living vendor specs.
- **No URLs** in the post itself. URLs live in `REFERENCES.md`.

## REFERENCES.md

The single bibliography for the whole series. Same author-org-first format,
with the URL appended:

```markdown
- Liu, N. F., et al., *"Lost in the Middle: How Language Models Use Long
  Contexts"* (TACL, 2024). https://arxiv.org/abs/2307.03172
```

Each post's "Further reading" section ends with:

> Full citations in [REFERENCES.md](../../REFERENCES.md).

## Numbers

Any number that appears in a post — a percentage, a benchmark score, a
token count, a price — must trace to a citation in that post's "Further
reading" section. No exceptions; if a citation cannot be produced, the
number does not go in.

## Self-citation

When citing other posts in this series, use a relative Markdown link with
the post number and short title:

```markdown
([Post 09](../09-rag-in-depth/index.md), §3)
```

Section anchors are by number (`§3`), not by slug, because section titles
shift more often than section numbers.
