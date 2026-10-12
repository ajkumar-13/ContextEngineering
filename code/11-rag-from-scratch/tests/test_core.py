"""Offline tests for the ragkit core. No network, no API key, stdlib + pytest only."""
from __future__ import annotations

from ragkit import BM25, chunk, rrf, split_sentences
from ragkit.pack import bookend_pack


def test_split_sentences():
    s = split_sentences("One sentence. Two! Three? Trailing")
    assert s == ["One sentence.", "Two!", "Three?", "Trailing"]


def test_chunk_respects_target_and_overlaps():
    # 20 sentences of 5 words each = 100 words total.
    text = " ".join("aa bb cc dd ee." for _ in range(20))
    chunks = chunk(text, target_tokens=25, overlap_tokens=10)
    assert len(chunks) >= 2
    # no chunk materially exceeds the target (a chunk may end exactly at the target)
    assert all(c.n_tokens <= 25 for c in chunks)
    # consecutive chunks overlap: the next chunk starts before the previous one ended
    assert chunks[1].start_sentence < chunks[0].start_sentence + len(chunks[0].text.split()) // 5


def test_chunk_never_drops_an_overlong_sentence():
    text = "word " * 40 + "."  # one 41-token sentence, bigger than the target
    chunks = chunk(text, target_tokens=10, overlap_tokens=3)
    assert len(chunks) == 1
    assert chunks[0].n_tokens == 41


def test_bm25_ranks_the_relevant_doc_first():
    docs = [
        "the cat sat on the mat",
        "reciprocal rank fusion merges ranked lists",
        "bm25 is a lexical retrieval baseline for keyword search",
    ]
    idx = BM25(docs)
    hits = idx.search("keyword retrieval baseline", top_k=3)
    assert hits[0][0] == 2  # the bm25 doc wins
    assert hits[0][1] > 0


def test_rrf_fuses_known_lists():
    dense = ["a", "b", "c"]
    lexical = ["b", "a", "d"]
    fused = rrf([dense, lexical], k=60)
    ids = [item for item, _ in fused]
    # 'b' is rank 2 then rank 1; 'a' is rank 1 then rank 2 -> 'a' and 'b' tie on score.
    # 'a' appears first overall, so the deterministic tie-break puts it ahead.
    assert ids[0] == "a"
    assert ids[1] == "b"
    assert set(ids) == {"a", "b", "c", "d"}


def test_rrf_rewards_agreement():
    # An item ranked highly by BOTH lists should beat an item ranked highly by one.
    fused = dict(rrf([["x", "y"], ["x", "z"]], k=60))
    assert fused["x"] > fused["y"]
    assert fused["x"] > fused["z"]


def test_bookend_pack_positions_the_two_strongest():
    packed = bookend_pack(["best", "second", "c", "d"])
    assert packed[0] == "best"
    assert packed[-1] == "second"
    assert packed[1:-1] == ["c", "d"]

def test_split_sentences_keeps_text_around_inner_full_stops():
    from ragkit import split_sentences

    text = "Standard delivery costs 4.95 dollars. See example.com for more. Done"
    assert split_sentences(text) == ["Standard delivery costs 4.95 dollars.", "See example.com for more.", "Done"]
    assert " ".join(split_sentences(text)).split() == text.split()
