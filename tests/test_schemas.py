"""Schema validation behaviour (the contract everything depends on)."""
import pytest

from packages.core.schemas.chunk import ParsedChunk
from packages.core.schemas.document import DocumentMeta
from packages.core.schemas.evidence import Answer, Citation, Claim


def test_chunk_id_format():
    assert ParsedChunk.make_chunk_id("d1", 12, 3, "docling") == "docling_d1_p12_c003"
    assert ParsedChunk.make_chunk_id("d1", 12, 3, "hybrid") == "hybrid_d1_p12_c003"
    # parser dimension prevents cross-parser Qdrant point collisions
    assert (
        ParsedChunk.make_chunk_id("d1", 12, 3, "baseline")
        != ParsedChunk.make_chunk_id("d1", 12, 3, "docling")
    )


def test_chunk_coerces_inverted_page_band():
    c = ParsedChunk(
        chunk_id="x", document_id="d", filename="a.pdf", page_start=5, page_end=2,
        chunk_text="t", token_count=1,
    )
    assert c.page_end == 5  # coerced up to page_start


def test_claim_requires_citation():
    with pytest.raises(ValueError):
        Claim(claim_id="c1", claim_text="unsupported", citations=[], evidence_ids=[])


def test_answer_supported_requires_citation():
    with pytest.raises(ValueError):
        Answer(question="q", answer_type="supported", answer="yes")


def test_answer_insufficient_forbids_claims():
    cit = Citation(filename="a.pdf", page=1, chunk_id="x")
    claim = Claim(claim_id="c1", claim_text="x", citations=[cit])
    with pytest.raises(ValueError):
        Answer(question="q", answer_type="insufficient_evidence", answer="no", claims=[claim])


def test_answer_round_trip():
    cit = Citation(filename="a.pdf", page=1, chunk_id="x")
    a = Answer(
        question="q", answer_type="supported", answer="yes",
        claims=[Claim(claim_id="c1", claim_text="yes", citations=[cit])],
        citations=[cit],
    )
    dumped = a.model_dump()
    again = Answer.model_validate(dumped)
    assert again.answer_type == "supported"


def test_document_merge_returns_copy():
    d = DocumentMeta(document_id="d", filename="a.pdf", domain="x", document_type="y")
    d2 = d.merge(parse_status="success", page_count=10)
    assert d.parse_status == "pending"
    assert d2.parse_status == "success" and d2.page_count == 10
