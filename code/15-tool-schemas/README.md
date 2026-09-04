# Tool schemas: budget & validation (`tool-schemas`)

Companion code for **[Post 15 — Tools and MCP](../../posts/15-tools-and-mcp/index.md)** and **[Post 21 — Structured output and guardrails](../../posts/21-structured-output-guardrails/index.md)**.

Two small, dependency-free utilities:

- **`budget`** — estimate the token and dollar cost of a tool catalogue, and show what trimming it saves. Every tool schema is rendered into the prompt on every call, competing for the same window as your data.
- **`validate`** — a minimal JSON-Schema-subset validator for structured output, returning a list of errors so it drops into a validate-and-retry loop.

## Quickstart

```bash
cd code/15-tool-schemas
python -m pip install -e ".[dev]"
pytest                 # passes with no key and no network
```

```python
from toolschemas import catalog_tokens, catalog_cost_usd, trim, validate

tools = [weather_tool, refund_tool, search_tool]           # your JSON schemas
print(catalog_tokens(tools), "tokens per call")
print(f"${catalog_cost_usd(tools):.4f} per call at ~$3/Mtok")
print(catalog_tokens(trim(tools, keep=2)), "tokens after trimming to 2")

errors = validate({"city": "Paris"}, weather_tool["input_schema"])
if errors:
    ...  # feed errors back to the model and retry (Post 21)
```

## What's stubbed / deliberately small

- **Token counts are estimated** with a bytes/token heuristic so the module runs offline; the *relative* comparison (is catalogue A cheaper than B) is what drives the design decision, and that holds. Count real tokens with the provider's tokenizer (Post 04) when you need exact numbers.
- **The validator covers the JSON-Schema subset a tool call uses** (type, required, properties, enum, `additionalProperties: false`, array items). Install the `schema` extra (`pip install '.[schema]'`) to use `pydantic`/`jsonschema` instead; install `api` to try provider-native structured output.
