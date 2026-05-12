from rag.ingest import chunk


def test_chunker_returns_chunks_under_target_plus_overlap():
    text = " ".join([f"Sentence number {i}." for i in range(400)])
    chunks = chunk(text)
    assert len(chunks) >= 2
    for c in chunks:
        # generous upper bound: target + overlap + a little slack
        assert len(c.split()) <= 500 + 80 + 25


def test_chunker_handles_short_text():
    chunks = chunk("Just one sentence here.")
    assert chunks == ["Just one sentence here."]


def test_chunker_handles_empty():
    assert chunk("") == []
