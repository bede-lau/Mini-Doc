"""Deterministic retrieval/citation/abstention metric behaviour."""
from packages.core.evaluation.scoring import (
    abstention_correctness,
    citation_page_match,
    hit_at_1,
    mean,
    mrr,
    recall_at_k,
)


def _hits(filenames):
    return [{"filename": f} for f in filenames]


def test_hit_at_1():
    assert hit_at_1(_hits(["a.pdf", "b.pdf"]), "a.pdf") == 1
    assert hit_at_1(_hits(["b.pdf", "a.pdf"]), "a.pdf") == 0
    assert hit_at_1([], "a.pdf") == 0


def test_recall_at_k():
    # a.pdf is 4th, so absent from top-3 but present in top-5
    hits = _hits(["b.pdf", "c.pdf", "d.pdf", "a.pdf"])
    assert recall_at_k(hits, "a.pdf", 3) == 0
    assert recall_at_k(hits, "a.pdf", 5) == 1


def test_mrr():
    hits = _hits(["b.pdf", "a.pdf", "c.pdf"])
    assert mrr(hits, "a.pdf") == 0.5
    assert mrr(hits, "z.pdf") == 0.0


def test_citation_page_match():
    c_in = [{"filename": "a.pdf", "page": 5}]
    c_out = [{"filename": "b.pdf", "page": 5}]
    assert citation_page_match(c_in, "a.pdf", None, None) == 1
    assert citation_page_match(c_in, "a.pdf", 4, 6) == 1
    assert citation_page_match(c_in, "a.pdf", 6, 8) == 0
    assert citation_page_match(c_out, "a.pdf", None, None) == 0
    assert citation_page_match([], "a.pdf", None, None) == 0


def test_abstention_correctness():
    assert abstention_correctness("insufficient_evidence", True) == 1
    assert abstention_correctness("supported", False) == 1
    assert abstention_correctness("insufficient_evidence", False) == 0
    assert abstention_correctness("supported", True) == 0


def test_mean():
    assert mean([1, 0, 1]) == round(2 / 3, 4)
    assert mean([]) == 0.0
