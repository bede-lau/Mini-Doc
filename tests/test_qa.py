"""Grounded Q&A + abstention behaviour (offline, deterministic path)."""
import json

from packages.core.config import Settings
from packages.core.generation.qa import _extract_json, build_api_answer, extractive_answer


def _hit(chunk_id, fn, page, text, score):
    from packages.core.schemas.evidence import RetrievalHit

    return RetrievalHit(
        chunk_id=chunk_id, document_id="d", filename=fn, page_start=page,
        page_end=page, chunk_text=text, score=score,
    )


def test_offline_grounded_answer_cites_exact_chunk():
    hits = [
        _hit("c1", "acra.pdf", 5,
             "A registrable controller is an individual or legal entity with significant "
             "interest or significant control over a company.", 0.82),
        _hit("c2", "dbs.pdf", 12, "Net profit rose ten percent.", 0.4),
    ]
    s = Settings(abstention_threshold=0.35)
    a = extractive_answer("Who qualifies as a registrable controller?", hits, s)
    assert a.answer_type == "supported"
    assert a.claims and a.citations
    # every claim is verbatim from a retrieved chunk and cites the right page
    for cl in a.claims:
        assert cl.claim_text in hits[0].chunk_text
        assert cl.citations[0].filename == "acra.pdf"
        assert cl.citations[0].page == 5


def test_offline_abstains_when_retrieval_below_threshold():
    hits = [_hit("c1", "x.pdf", 1, "Unrelated rainfall averages and humidity data.", 0.2)]
    a = extractive_answer("Who qualifies as a registrable controller?", hits, Settings())
    assert a.answer_type == "insufficient_evidence"
    assert a.answer.startswith("Insufficient evidence")


def test_offline_abstains_when_no_term_overlap():
    hits = [_hit("c1", "x.pdf", 1,
                 "Annual rainfall averaged 2400mm with dense vegetation across the region.", 0.9)]
    a = extractive_answer("Who qualifies as a registrable controller?", hits, Settings())
    assert a.answer_type == "insufficient_evidence"


def test_api_answer_drops_ungrounded_claims():
    hits = [_hit("c1", "acra.pdf", 5, "A controller has significant interest.", 0.8)]
    raw = json.dumps({
        "answer_type": "supported",
        "answer": "yes",
        "claims": [
            {"claim_text": "grounded", "chunk_ids": ["c1"]},
            {"claim_text": "hallucination", "chunk_ids": ["FAKE"]},
        ],
    })
    a = build_api_answer("q", raw, hits, Settings())
    assert len(a.claims) == 1
    assert a.claims[0].citations[0].chunk_id == "c1"


def test_api_answer_respects_model_abstention():
    hits = [_hit("c1", "x.pdf", 1, "Some text.", 0.8)]
    raw = json.dumps({"answer_type": "insufficient_evidence", "answer": "no", "claims": []})
    a = build_api_answer("q", raw, hits, Settings())
    assert a.answer_type == "insufficient_evidence"


def test_api_answer_degrades_to_extractive_on_bad_json():
    hits = [_hit("c1", "acra.pdf", 5,
                 "A registrable controller has significant interest or significant control.", 0.8)]
    a = build_api_answer("Who is a controller?", "this is not json", hits, Settings(abstention_threshold=0.35))
    assert a.answer_type == "supported"
    assert a.citations


def test_offline_answer_skips_heading_fragments_and_formats_bullets():
    hits = [
        _hit("heading", "mas-trm.pdf", 7, "3 Technology Risk Governance and Oversight", 0.91),
        _hit(
            "c1",
            "mas-trm.pdf",
            8,
            "ensuring a sound and robust risk management framework is established and maintained to manage technology risks;",
            0.9,
        ),
        _hit(
            "c2",
            "mas-trm.pdf",
            8,
            "ensuring there is a technology risk management function to oversee the technology risk management framework and strategy;",
            0.89,
        ),
    ]

    a = extractive_answer(
        "What are the key expectations around technology risk governance?",
        hits,
        Settings(abstention_threshold=0.35),
    )

    assert a.answer_type == "supported"
    assert "3 Technology Risk Governance" not in a.answer
    assert a.answer.startswith("Based on the cited evidence:")
    assert "- Ensuring" in a.answer
    assert all(cl.claim_text in {hits[1].chunk_text, hits[2].chunk_text} for cl in a.claims)


def test_extract_json_handles_fences_and_garbage():
    assert _extract_json("```json\n{\"a\":1}\n```") == {"a": 1}
    assert _extract_json("prefix {\"b\":2} suffix") == {"b": 2}
    assert _extract_json("no json here") is None
