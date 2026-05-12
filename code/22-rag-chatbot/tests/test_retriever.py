from rag.retrieve import rrf_merge


def test_rrf_merge_prefers_consistently_top_items():
    a = ["x", "y", "z"]
    b = ["y", "x", "z"]
    merged = rrf_merge([a, b])
    # 'y' appears at rank 0 and 0; 'x' at 0 and 1; both should beat 'z'.
    assert merged[-1] == "z"
    assert set(merged[:2]) == {"x", "y"}


def test_rrf_merge_handles_disjoint_rankings():
    merged = rrf_merge([["a", "b"], ["c", "d"]])
    assert set(merged) == {"a", "b", "c", "d"}
