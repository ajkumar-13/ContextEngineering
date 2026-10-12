# context_inspector.py: assemble one request body from the six layers and print it
import json
from typing import Any

LAYERS = {
    1: "System prompt",
    2: "Tools and MCP descriptions",
    3: "Memory and state",
    4: "Retrieved chunks",
    5: "Conversation history",
    6: "User instruction",
}


def assemble_context(
    *,
    system_prompt: str,
    tool_schemas: list[dict[str, Any]],
    memory: list[str],
    retrieved_chunks: list[str],
    history: list[dict[str, str]],
    user_instruction: str,
) -> tuple[dict[str, Any], list[tuple[str, int]]]:
    """Return a request body in Anthropic Messages shape and the layer of every entry."""
    messages: list[dict[str, str]] = []
    layer_map: list[tuple[str, int]] = [("system", 1)]
    layer_map += [(f"tools[{i}]", 2) for i in range(len(tool_schemas))]

    def add(message: dict[str, str], layer: int) -> None:
        layer_map.append((f"messages[{len(messages)}]", layer))
        messages.append(message)

    # Layer 03: memory replayed as a synthetic exchange
    if memory:
        notes = "\n".join(memory)
        add({"role": "user", "content": f"<memory>{notes}</memory>"}, 3)
        add({"role": "assistant", "content": "Acknowledged."}, 3)

    # Layer 04: retrieved chunks as a user-side evidence block
    if retrieved_chunks:
        evidence = "\n".join(f"<chunk>{c}</chunk>" for c in retrieved_chunks)
        add({"role": "user", "content": evidence}, 4)

    # Layer 05: the prior turns of this session
    for turn in history:
        add(turn, 5)

    # Layer 06: the current user turn, placed last
    add({"role": "user", "content": user_instruction}, 6)

    body = {
        "system": system_prompt,  # layer 01
        "tools": tool_schemas,  # layer 02
        "messages": messages,  # layers 03 to 06
        "model": "claude-sonnet-4-5",  # illustrative; model ids change over time
        "max_tokens": 1024,
    }
    return body, layer_map


def render(body: dict[str, Any]) -> str:
    """JSON with one entry per line (a long entry spread over several lines)."""
    lines = ["{"]
    for n, (key, value) in enumerate(body.items()):
        comma = "," if n < len(body) - 1 else ""
        if isinstance(value, list):
            lines.append(f'  "{key}": [')
            for i, item in enumerate(value):
                sep = "," if i < len(value) - 1 else ""
                text = json.dumps(item)
                if len(text) > 76:
                    text = json.dumps(item, indent=2).replace("\n", "\n    ")
                lines.append("    " + text + sep)
            lines.append("  ]" + comma)
        else:
            lines.append(f'  "{key}": {json.dumps(value)}{comma}')
    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    body, layer_map = assemble_context(
        system_prompt="You are a helpful research assistant.",
        tool_schemas=[{"name": "search_docs", "description": "Search the product docs.",
                       "input_schema": {"type": "object"}}],
        memory=["User prefers Python."],
        retrieved_chunks=["Webhooks are HTTP callbacks."],
        history=[
            {"role": "user", "content": "How do webhooks work?"},
            {"role": "assistant", "content": "A webhook is an HTTP callback."},
        ],
        user_instruction="Now show me how to rotate the signing secret.",
    )
    print(render(body))
    print()
    print("layer map:")
    for path, layer in layer_map:
        print(f"  {path:<12} {layer:02d} {LAYERS[layer]}")
