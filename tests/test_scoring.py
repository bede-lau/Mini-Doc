"""Deterministic retrieval/citation/abstention metric behaviour."""
from packages.core.evaluation.scoring import (
    abstention_correctness,
    citation_page_match,
    hit_at_1,
    mean,
    mrr,
    recall_at_k,
)
from packages.core.evaluation.benchmark import load_run_result


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


def test_load_run_result_reads_saved_scores(settings):
    out_dir = settings.results_dir / "run_test"
    out_dir.mkdir(parents=True)
    (out_dir / "scores.csv").write_text(
        "\n".join(
            [
                "question_id,hit_at_1,recall_at_3,recall_at_5,mrr,citation_page_match,abstention_correctness,answer_type,unsupported_claim_count",
                "q1,1,1,1,1.0,1,1,supported,0",
                "q2,0,1,1,0.5,0,1,insufficient_evidence,2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = load_run_result("run_test", settings=settings)

    assert result["run_id"] == "run_test"
    assert result["questions"] == 2
    assert result["summary"]["hit_at_1"] == 0.5
    assert result["summary"]["insufficient_evidence_answers"] == 1
    assert result["summary"]["unsupported_claim_total"] == 2


def test_load_run_result_rejects_path_traversal(settings):
    try:
        load_run_result("../run_test", settings=settings)
    except ValueError as exc:
        assert "invalid run_id" in str(exc)
    else:
        raise AssertionError("expected invalid run_id")
