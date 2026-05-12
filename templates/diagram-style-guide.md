# Diagram style guide

Every diagram in this series uses the same visual language. Departures look
out of place; adherence makes the whole repository feel like one book.

---

## Palette

```
:root {
  --ce-bg:      #FAFAF7;     /* page background */
  --ce-surface: #FFFFFF;     /* cards, boxes */
  --ce-ink:     #1A1A1A;     /* text, primary strokes */
  --ce-primary: #5B7FBF;     /* primary fills, links */
  --ce-accent:  #D98E5F;     /* secondary fills */
  --ce-success: #5C9E78;     /* "good" outcomes */
  --ce-warn:    #B8895A;     /* "caution" */
  --ce-alert:   #C66B5E;     /* "bad" outcomes */
  --ce-grid:    rgba(26,26,26,0.06);
  --ce-muted:   #6B6B6B;     /* secondary text */
}

@media (prefers-color-scheme: dark) {
  :root {
    --ce-bg:      #161512;
    --ce-surface: #1E1D1A;
    --ce-ink:     #F1EEE8;
    --ce-primary: #8BA8E0;
    --ce-accent:  #E8B088;
    --ce-success: #7FBF9B;
    --ce-warn:    #D4B58A;
    --ce-alert:   #D88880;
    --ce-grid:    rgba(241,238,232,0.08);
    --ce-muted:   #A6A29B;
  }
}
```

Every SVG **inlines this `<style>` block** in its own `<defs>`. There is
no shared external stylesheet — diagrams must render correctly when
embedded as `<img>`, opened standalone, or pasted into a static-site
generator.

## Typography

- **Labels:** Inter, 12–14 px for body, 16–20 px for titles.
- **Code / monospace labels:** JetBrains Mono, 12 px.
- All text is `<text>` elements; never images of text.
- Letter-spacing 0; line-height 1.3.

## Strokes

- Primary structural lines: **1.5 px**.
- Secondary lines (annotations, leader lines): **1.0 px**.
- Grid lines: **0.75 px**, `var(--ce-grid)`.
- Stroke colour `var(--ce-ink)` unless otherwise needed.

## Fills

- Boxes / nodes: `var(--ce-surface)` interior, `var(--ce-ink)` 1.5 stroke.
- Highlight colour follows semantics:
  - `--ce-primary` for the canonical / default object.
  - `--ce-success` for "what worked" / "after".
  - `--ce-alert` for "what failed" / "before".
  - `--ce-accent` for the secondary contrast.

## Layout

- `viewBox` set; no fixed `width` / `height` on the root `<svg>`.
- Padding: at least 24 px around the bounding content.
- Aspect ratios: 16:9 for hero; 4:3 for inline; 1:1 for icon.

## Filenames

`assets/diagrams/exports/NN-short-name.svg`, where `NN` matches the post
number (or `NN.M` for multiple diagrams in one post). Source files live
in `assets/diagrams/src/` with the same stem.

## Accessibility

- Every `<svg>` has a `<title>` and `<desc>` element.
- Foreground / background pairs pass WCAG AA in both light and dark
  palettes (already true for the values above).
- Do not encode information in colour alone — pair colour with shape,
  position, or text.

## Checklist

Before merging a new diagram:

- [ ] Inlines the `:root` variables and `@media` block.
- [ ] Uses only the eight semantic colours plus muted/grid.
- [ ] Inter for labels; JetBrains Mono for code.
- [ ] Strokes 1.5 / 1.0 / 0.75 only.
- [ ] `viewBox` set; no fixed dimensions on root.
- [ ] Has `<title>` and `<desc>`.
- [ ] Renders correctly in both light and dark mode.
