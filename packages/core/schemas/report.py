"""Compliance report data model.

The renderer (reporting/renderer.py) consumes a Report and emits the
compliance-review template. Keeping data and rendering separate makes the report
testable and the template easy to evolve.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReportType = Literal[
    "kyc_beneficial_ownership",
    "technology_risk_compliance",
    "insurance_claims_review",
    "general_compliance_intelligence",
]

Severity = Literal["Critical", "High", "Medium", "Low", "Informational"]
FindingStatus = Literal["Supported", "Partial", "Insufficient Evidence", "Conflicting Evidence"]
FactType = Literal["extracted_fact", "inferred_conclusion", "missing_information", "contradiction"]


class ReportFinding(BaseModel):
    finding_id: str
    title: str
    status: FindingStatus = "Supported"
    risk_level: Severity = "Informational"
    claim: str
    evidence: str
    source_filename: str
    page: int | None = None
    section: str | None = None
    analyst_note: str | None = None


class ReportFact(BaseModel):
    fact_id: str
    fact: str
    type: FactType = "extracted_fact"
    source: str
    page: int | None = None
    evidence_quote: str = ""
    confidence: float = 0.0


class ReportRiskFlag(BaseModel):
    risk_id: str
    risk: str
    severity: Severity = "Medium"
    evidence: str = ""
    source: str = ""
    recommended_next_step: str = ""


class ReportMissingItem(BaseModel):
    missing_item: str
    why_it_matters: str
    required_source: str = ""
    impact: str = ""


class ReportConflict(BaseModel):
    conflict_id: str
    conflict: str
    source_a: str = ""
    source_b: str = ""
    resolution_status: str = "Open"


class ReportSection(BaseModel):
    """An arbitrary named section with optional table rows (list of dicts)."""

    title: str
    intro: str | None = None
    bullets: list[str] = Field(default_factory=list)
    table_columns: list[str] = Field(default_factory=list)
    table_rows: list[dict] = Field(default_factory=list)
    findings: list[ReportFinding] = Field(default_factory=list)


class ReportConfig(BaseModel):
    """Appendix C — model and parser configuration, captured for auditability."""

    parser: str = "docling"
    chunk_size: int = 0
    chunk_overlap: int = 0
    embedding_model: str = ""
    vector_db: str = "Qdrant"
    retrieval_top_k: int = 0
    reranking: str = "none (dense only)"
    llm_model: str = "offline (extractive)"
    temperature: float = 0.0


class Report(BaseModel):
    report_id: str
    prepared_for: str = "Mini-Doc Review Workspace"
    prepared_by: str = "Mini-Doc"
    prepared_date: str
    document_bundle: str
    confidentiality: str = "Public demo data only"
    disclaimer: str = (
        "This is a technical work sample using public/synthetic documents. It is "
        "not legal, financial, insurance, or regulatory advice."
    )
    documents: list[dict] = Field(default_factory=list)
    executive_summary: ReportSection
    scope: ReportSection
    inventory: ReportSection
    findings: list[ReportFinding] = Field(default_factory=list)
    facts: list[ReportFact] = Field(default_factory=list)
    risk_flags: list[ReportRiskFlag] = Field(default_factory=list)
    missing: list[ReportMissingItem] = Field(default_factory=list)
    conflicts: list[ReportConflict] = Field(default_factory=list)
    evidence_table_rows: list[dict] = Field(default_factory=list)
    next_actions: list[dict] = Field(default_factory=list)
    retrieval_log: list[dict] = Field(default_factory=list)
    benchmark_summary: str | None = None
    config: ReportConfig
