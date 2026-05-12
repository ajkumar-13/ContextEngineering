# NN · TITLE — companion code

One paragraph: what this code is, which post it accompanies, what
shape of system it implements.

## Quickstart

```powershell
cd code/NN-name
uv sync                          # or: pip install -e .
copy .env.example .env           # then edit with your API keys
uv run python -m PACKAGE.MODULE
```

## Required keys

List every environment variable, with the provider and the cheap /
local alternative for each one.

## Layout

```
.
├── README.md
├── pyproject.toml
├── .env.example
├── data/                        # any starter data
├── prompts/                     # system prompts as files
├── src/PACKAGE/                 # the actual code
└── tests/
```

## What's wired

- Bullet list of components actually implemented.

## What's deliberately stubbed

- Bullet list of things left as TODOs, with pointers to where to look.

## License

MIT for code; CC BY 4.0 for prose. See repo root.
