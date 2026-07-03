"""Evidence, claims, citations, retrieval hits, and answers.

These models enforce the core grounding rules: a material claim must carry at
least one citation, and every answer stores the raw retrieved chunks that
backed it.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

AnswerType = Literal["supported", "insufficient_evidence", "conflicting_evidence"]
SupportLevel = Literal["direct", "partial", "weak", "contradictory"]


class RetrievalHit(BaseModel):
    """One retrieved chunk with its relevance score and full provenance."""

    chunk_id: str
    document_id: str
    filename: str
    page_start: int
    page_end: int
    section: str | None = None
    chunk_text: str
    chunk_type: str = "paragraph"
    parser: str = "baseline"
    score: float = 0.0
    source_url: str | None = None

    @property
    def page(self) -> int:
        return self.page_start


class Citation(BaseModel):
    filename: str
    page: int
    chunk_id: str
    section: str | None = None

    @property
    def label(self) -> str:
        loc = f"{self.filename}, p.{self.page}"
        if self.section:
            loc += f" ({self.section})"
        return loc


class Claim(BaseModel):
    claim_id: str
    claim_text: str
    evidence_ids: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_citation(self) -> "Claim":
        # Core rule: no citation, no claim. A material claim must be grounded.
        if not self.citations and not self.evidence_ids:
            raise ValueError(
                f"Claim {self.claim_id!r} has no citations and no evidence ids — "
                "every material claim must be grounded."
            )
        return self


class Evidence(BaseModel):
    evidence_id: str
    claim_id: str
    chunk_id: str
    document_title: str | None = None
    filename: str
    page: int
    section: str | None = None
    evidence_quote: str
    support_level: SupportLevel = "partial"
    confidence: float = 0.0


class Answer(BaseModel):
    """A grounded answer to a single question."""

    question: str
    answer_type: AnswerType
    answer: str
    claims: list[Claim] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: list[RetrievalHit] = Field(default_factory=list)

    @model_validator(mode="after")
    def _abstention_shape(self) -> "Answer":
        # When we abstain, the prose must say so and there must be no ungrounded
        # claims. Supported answers must carry at least one citation.
        if self.answer_type == "insufficient_evidence":
            if self.claims:
                raise ValueError("insufficient_evidence answers must not assert claims")
        elif self.answer_type == "supported":
            if not self.citations:
                raise ValueError("supported answers must include at least one citation")
        return self
