# rolling_summary.py: fold each new batch of turns into one running summary
#
# Run from the series root:  uv run python posts/12-compress-strategies/snippets/rolling_summary.py
# Offline by default: it prints the prompt the first fold would send, and makes no model call. To fold with a
# real model, install the Anthropic SDK, set ANTHROPIC_API_KEY, and pass anthropic_complete to fold().

MODEL = "claude-sonnet-4-5"  # one of the series' running models as of early 2026; check the provider's page


def fold_prompt(summary: str, new_turns: list[str], target_tokens: int = 300) -> str:
    """The prompt that folds new turns into a running summary, preserving decisions and facts."""
    prior = f"Existing summary:\n{summary}\n\n" if summary else ""
    convo = "\n".join(new_turns)
    return (
        f"{prior}New turns to fold in:\n{convo}\n\n"
        "Rewrite the summary for the agent that will continue this conversation. "
        "Preserve, in order: decisions and their reasoning; open questions; "
        "user-stated facts and preferences; tool conclusions (not verbatim output). "
        f"No politeness or filler. Bullet points, <= {target_tokens} tokens."
    )


def fold(summary, new_turns, complete, target_tokens=300):
    """complete(prompt, max_tokens) -> text is any model call; the summary it returns replaces the old one."""
    return complete(fold_prompt(summary, new_turns, target_tokens), target_tokens + 100)


def anthropic_complete(prompt, max_tokens):
    from anthropic import Anthropic  # imported here so that the offline run needs no SDK

    msg = Anthropic().messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def main():
    batch = [
        "user: I am Priya; the project lead is Alice Moreno and we run Postgres 16.",
        "user: Find out why the nightly export job fails.",
        "tool search_logs: (120 rows) ERROR export: disk quota exceeded on /var/exports",
        "user: Decision: move the exports to the bucket acme-exports instead of a bigger disk.",
    ]
    print(fold_prompt("", batch))


if __name__ == "__main__":
    main()
