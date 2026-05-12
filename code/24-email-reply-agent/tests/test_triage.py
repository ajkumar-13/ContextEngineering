import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from emailbot.triage import VALID_BUCKETS  # noqa: E402


def test_valid_buckets_are_the_four_documented():
    assert VALID_BUCKETS == {
        "reply_needed", "info_only", "promotional", "automated_no_reply",
    }
