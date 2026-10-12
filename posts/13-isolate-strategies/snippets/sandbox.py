# sandbox.py: run a noisy command in a child process and return only the structured result
#
# Run from the series root:  uv run python posts/13-isolate-strategies/snippets/sandbox.py
# Needs tiktoken (in the root environment, encodings cached); no network call. The "install" is a
# stand-in child process that prints a long, package-manager-style log; nothing is installed.
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import tiktoken

ENC = tiktoken.get_encoding("o200k_base")

# The stand-in command: 120 packages fetched, every tenth one deprecated, then a summary line.
FAKE_INSTALL = r"""
for i in range(120):
    print(f"fetch  pkg-{i:03d}@1.{i % 7}.{i % 5}  resolved from the registry cache")
    if i % 10 == 0:
        print(f"warn deprecated pkg-{i:03d}@1.{i % 7}.{i % 5}: upgrade to 2.x")
print("added 120 packages in 8s")
"""


def run_sandboxed(cmd, log_path):
    """Run cmd, keep the full output in log_path, and return the few fields the model needs."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    lines = proc.stdout.splitlines()
    return {"ok": proc.returncode == 0, "exit_code": proc.returncode,
            "warnings": sum(line.startswith("warn") for line in lines),
            "summary": lines[-1] if lines else "", "log": log_path.name}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "install.log"
        result = run_sandboxed([sys.executable, "-c", FAKE_INSTALL], log_path)
        full = log_path.read_text(encoding="utf-8")
    returned = json.dumps(result)
    n_full, n_returned = len(ENC.encode(full)), len(ENC.encode(returned))
    print(f"full log: {len(full.splitlines())} lines, {n_full} tokens (kept in {result['log']})")
    print(f"returned to the model: {returned}")
    print(f"{n_returned} tokens, {n_full / n_returned:.0f} times fewer than the full log")
