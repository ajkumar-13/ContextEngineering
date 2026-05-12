import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from emailbot.send_gate import send_gate  # noqa: E402


def _thread(body: str) -> list[dict]:
    return [{"from": "x@y.com", "subject": "s", "body": body}]


def test_send_gate_ok_on_clean_draft():
    d = "Hi Anika,\n\nThursday at 14:00 IST works. Best, Shrirat"
    assert send_gate(d, _thread("Following up. Best, Anika")).ok


def test_send_gate_blocks_unknown_url():
    d = "See https://malicious.example/x for details."
    assert not send_gate(d, _thread("Hi.")).ok


def test_send_gate_allows_url_present_in_thread():
    thread = _thread("My profile: https://example.com/me")
    d = "Got it — https://example.com/me confirmed."
    assert send_gate(d, thread).ok


def test_send_gate_blocks_introduced_money():
    assert not send_gate("Sure, $500 sounds fine.", _thread("Could we work together?")).ok


def test_send_gate_blocks_non_business_hour_time():
    assert not send_gate("How about 22:00 on Thursday?", _thread("When can we meet?")).ok


def test_send_gate_allows_business_hour_time():
    assert send_gate("How about 14:00 on Thursday?", _thread("When can we meet?")).ok
