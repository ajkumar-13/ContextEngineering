# orchestrator.py: a framework-free orchestrator and one worker with a typed contract
#
# Run from the series root:  uv run python posts/13-isolate-strategies/snippets/orchestrator.py
# Needs tiktoken (in the root environment, encodings cached); no network call and no API key.
# The worker's model is a scripted stand-in that makes the tool calls a model would make, so the
# snippet runs offline. What it shows is the bookkeeping: which tokens land in which window.
import json
from dataclasses import asdict, dataclass

import tiktoken

ENC = tiktoken.get_encoding("o200k_base")


def tokens(window):
    """Tokens of a context window, counted over the content of its messages."""
    return sum(len(ENC.encode(m["content"])) for m in window)


# The suite the worker runs: three files, 75 tests, two failing. run_tests returns a verbose log,
# one line per test and a traceback per failure, in the manner of pytest -v.
SUITE = {
    "tests/test_api.py": (30, []),
    "tests/test_db.py": (25, ["test_migration_rollback"]),
    "tests/test_auth.py": (20, ["test_token_expiry"]),
}


def run_tests(path):
    n, failing = SUITE[path]
    names = sorted(failing + [f"test_case_{i:02d}" for i in range(n - len(failing))])
    lines = []
    for k, name in enumerate(names, 1):
        status = "FAILED" if name in failing else "PASSED"
        lines.append(f"{path}::{name} {status} [{100 * k // n:3d}%]")
    for name in failing:
        lines += [f"____ {name} ____", "Traceback (most recent call last):",
                  f'  File "{path}", line 42, in {name}', "    assert result == expected",
                  "AssertionError: assert 3 == 4"]
    return "\n".join(lines)


@dataclass(frozen=True)
class TestTask:  # the input contract: everything the worker needs, and nothing else
    paths: list[str]


@dataclass(frozen=True)
class TestReport:  # the output contract: structured and finite
    passed: int
    failed: list[str]


def validate(raw: str) -> TestReport:
    """Check the worker's reply against the output contract before the parent uses it."""
    data = json.loads(raw)  # a prose reply fails here
    ok = (isinstance(data, dict) and set(data) == {"passed", "failed"}
          and isinstance(data["passed"], int) and isinstance(data["failed"], list)
          and all(isinstance(name, str) for name in data["failed"]))
    if not ok:
        raise ValueError("the reply does not match the output contract")
    return TestReport(data["passed"], data["failed"])


WORKER_SYSTEM = ('You are the test-runner sub-agent. Run the test files you are given and reply only '
                 'with JSON: {"passed": <int>, "failed": [<file::test>, ...]}.')


def worker(task: TestTask) -> tuple[str, list[dict]]:
    """Run in a fresh window and return the reply and that window, which the parent never sees."""
    window = [{"role": "system", "content": WORKER_SYSTEM},
              {"role": "user", "content": json.dumps(asdict(task))}]
    passed, failed = 0, []
    for path in task.paths:  # the scripted stand-in for the model's tool calls
        window.append({"role": "assistant", "content": f"run_tests({path!r})"})
        log = run_tests(path)
        window.append({"role": "tool", "content": log})
        for line in log.splitlines():
            if line.endswith("%]"):
                name, status = line.split()[:2]
                passed += status == "PASSED"
                failed += [name] if status == "FAILED" else []
    reply = json.dumps({"passed": passed, "failed": failed})
    window.append({"role": "assistant", "content": reply})
    return reply, window


def orchestrate():
    """The parent delegates one task and keeps only the validated result."""
    parent = [{"role": "system", "content": "You are the release agent. Delegate test runs, then "
                                            "decide whether the release can ship."},
              {"role": "user", "content": "Can release 2.4 ship?"}]
    before = tokens(parent)
    reply, worker_window = worker(TestTask(paths=list(SUITE)))
    report = validate(reply)
    parent.append({"role": "tool", "content": json.dumps(asdict(report))})
    return parent, worker_window, before, report


if __name__ == "__main__":
    parent, worker_window, before, report = orchestrate()
    log_lines = [ln for p in SUITE for ln in run_tests(p).splitlines()]
    leaked = [ln for ln in log_lines if any(ln in m["content"] for m in parent)]
    assert not leaked and report.passed + len(report.failed) == 75
    print(f"worker window: {len(worker_window)} messages, {tokens(worker_window)} tokens "
          f"({len(SUITE)} test logs, {len(log_lines)} log lines)")
    print(f"parent window: {before} tokens before the call, {tokens(parent)} after "
          f"(+{tokens(parent) - before})")
    print(f"returned to the parent: {parent[-1]['content']}")
    print(f"log lines in the parent window: {len(leaked)}")
    try:
        validate("All tests passed except two, see above.")
    except ValueError as err:  # json.JSONDecodeError is a ValueError
        print(f"a prose reply is rejected by the contract check: {type(err).__name__}")
