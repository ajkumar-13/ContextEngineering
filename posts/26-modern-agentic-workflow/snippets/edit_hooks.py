"""Two edit hooks in Claude Code's command-hook protocol, and a demo that drives them as the host does (post 26).

Run from the series root:  uv run python posts/26-modern-agentic-workflow/snippets/edit_hooks.py

As a hook, the host runs `python edit_hooks.py guard` before an Edit or Write tool call (PreToolUse) and
`python edit_hooks.py compile_check` after one (PostToolUse). The host sends the event as JSON on standard
input; the hook answers with its exit code, and on exit code 2 its standard error is the message the model
reads (Anthropic, "Hooks reference", Claude Code documentation, consulted October 2026). With no argument, the
script builds a throwaway project in a temporary directory and runs itself as a hook five times. Standard
library only; nothing outside the temporary directory is touched.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROTECTED = ("vendor", "legacy")   # directories the agent may read but never edit


def guard(event):
    """PreToolUse on Edit|Write: block an edit outside the project or inside a protected directory."""
    root = Path(event["cwd"]).resolve()
    target = (root / event["tool_input"]["file_path"]).resolve()
    if not target.is_relative_to(root):
        return 2, "blocked: the file is outside the project."
    top = target.relative_to(root).parts[0]
    if top in PROTECTED:
        return 2, f"blocked: {top}/ is read-only here; change the code that calls it."
    return 0, ""


def compile_check(event):
    """PostToolUse on Edit|Write: report a Python file that no longer compiles back to the model."""
    path = Path(event["cwd"]) / event["tool_input"]["file_path"]
    if path.suffix != ".py":
        return 0, ""
    try:
        compile(path.read_text(encoding="utf-8"), path.name, "exec")   # parse only; nothing is written
    except SyntaxError as err:
        return 2, f"{path.name} line {err.lineno}: {err.msg}."
    return 0, ""


HOOKS = {"guard": guard, "compile_check": compile_check}


def hook_main(name):
    """The hook entry point: read the event from standard input, answer with an exit code."""
    code, message = HOOKS[name](json.load(sys.stdin))
    if message:
        print(message, file=sys.stderr)
    sys.exit(code)


def demo():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "acme-api"
        for folder in ("app", "vendor"):
            (root / folder).mkdir(parents=True)
        (root / "app" / "orders.py").write_text("def total(items):\n    return sum(items)\n", encoding="utf-8")
        (root / "app" / "refunds.py").write_text("def refund(order)\n    return order.total\n", encoding="utf-8")
        cases = [
            ("PreToolUse", "guard", "Edit", "app/orders.py"),
            ("PreToolUse", "guard", "Edit", "vendor/payments.py"),
            ("PreToolUse", "guard", "Write", "../.env"),
            ("PostToolUse", "compile_check", "Edit", "app/orders.py"),
            ("PostToolUse", "compile_check", "Edit", "app/refunds.py"),
        ]
        for event_name, hook, tool, path in cases:
            event = {"hook_event_name": event_name, "cwd": str(root), "tool_name": tool,
                     "tool_input": {"file_path": str(root / path)}}   # the host sends absolute paths
            run = subprocess.run([sys.executable, __file__, hook], input=json.dumps(event),
                                 capture_output=True, text=True, timeout=30)
            said = run.stderr.strip() or ("allowed" if event_name == "PreToolUse" else "passed")
            print(f"{event_name:<12} {tool:<6} {path:<19} exit {run.returncode}  {said}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in HOOKS:
        hook_main(sys.argv[1])
    else:
        demo()
