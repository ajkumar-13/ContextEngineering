"""Post 30: load the offline parts of the companion without its runtime dependencies.

Not run on its own: drafter_request.py and send_gate_cases.py import it. The companion's package
`emailbot` imports python-dotenv on import, and its modules `llm`, `replies` and `draft` import the
openai, chromadb and voyageai packages at module level, so importing them needs those packages installed.
The parts this post runs offline are standard library: `send_gate.py` and `memory.py` are loaded whole
from their files, and the functions `_render_thread` (draft.py), `pack_prior_replies` and `_embed`
(replies.py) are compiled from their exact source text, so the post runs the companion's own code and
not a copy of it.
"""
import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPANION = ROOT / "code" / "30-email-reply-agent"
SRC = COMPANION / "src" / "emailbot"


def load_module(name: str):
    """Load one stdlib-only module of the companion from its file, bypassing the package __init__."""
    spec = importlib.util.spec_from_file_location(f"emailbot_{name}", SRC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod   # dataclasses look the module up while the class is built
    spec.loader.exec_module(mod)
    return mod


def load_function(file: str, name: str, env: dict | None = None):
    """Compile one top-level function of a companion file from its source text, with the globals in env."""
    path = SRC / file
    text = path.read_text(encoding="utf-8")
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns: dict = dict(env or {})
    exec(compile("from __future__ import annotations\n" + ast.get_source_segment(text, node), str(path), "exec"), ns)
    return ns[name]


def source(file: str) -> str:
    return (SRC / file).read_text(encoding="utf-8")


if __name__ == "__main__":
    print("helper module: run drafter_request.py or send_gate_cases.py")
