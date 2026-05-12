# Diagram Style System

All diagrams in this series share one design language so a reader who has seen one diagram can immediately read the next.

## Files in this folder

| File           | Purpose                                                                                        |
| -------------- | ---------------------------------------------------------------------------------------------- |
| `tokens.json`  | Machine-readable design tokens. Source of truth for any tooling.                               |
| `tokens.css`   | Same tokens as CSS variables. **Inline into every standalone SVG** via a `<style>` block.      |
| `README.md`    | This file. Rules of the visual system.                                                         |

## Rules

1. **Inline the stylesheet.** Every published `.svg` must include the contents of `tokens.css` inside a `<style>` element so the SVG is self-contained and renders identically anywhere it is embedded.
2. **Light and dark.** `tokens.css` defines a default light palette and a `prefers-color-scheme: dark` block. No diagram should hard-code colours; always reference `var(--ce-*)`.
3. **Type.** Labels use Inter; code uses JetBrains Mono. If those fonts are unavailable the system fallback chain in the tokens applies.
4. **Strokes.** Primary lines are `1.5 px`; secondary `1 px`; hairlines `0.75 px`; dashed lines use `stroke-dasharray: 4 3`.
5. **Sizing.** Every diagram is authored for a 960 px display width. Internal coordinates use a `viewBox` so the SVG scales cleanly to any container width.
6. **Accessibility.** Every diagram defines `<title>` and `<desc>` at the root for screen readers, plus a separate caption written into the post's Markdown.
7. **No raster text.** Text must remain text in the SVG, never converted to paths.

## How to edit a diagram

1. Open the `.svg` directly in VS Code, a browser, or Figma (via SVG import).
2. Modify shapes in the editor of choice; do not change `class` names — they bind to the shared tokens.
3. Re-export over the existing file path so any `<img>` references in posts continue to work.

## Adding a new colour

If a diagram needs a colour not in `tokens.json`:

1. Add it to `tokens.json` and `tokens.css` first (light + dark).
2. Document its semantic meaning in this README.
3. Then use it in the diagram via `var(--ce-newname)`.

Never inline a hex value in an SVG. Tokens only.
