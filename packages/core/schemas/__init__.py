"""Pydantic schemas — the single source of truth for all data shapes.

Every module (parsers, retrieval, generation, reporting, evaluation, API) is
typed against these models, so the pipeline stays coherent end to end.
"""
from packages.core.schemas.chunk import ChunkType, ParsedChunk
from packages.core.schemas.document import DocumentMeta, ParseStatus
from packages.core.schemas.evidence import (
    Answer,
    AnswerType,
    Citation,
    Claim,
    Evidence,
    RetrievalHit,
    SupportLevel,
)
from packages.core.schemas.report import (
    Report,
    ReportConflict,
    ReportFact,
    ReportFinding,
    ReportRiskFlag,
    ReportSection,
    ReportType,
)
from packages.core.schemas import api

__all__ = [
    "ChunkType",
    "ParsedChunk",
    "DocumentMeta",
    "ParseStatus",
    "Answer",
    "AnswerType",
    "Citation",
    "Claim",
    "Evidence",
    "RetrievalHit",
    "SupportLevel",
    "Report",
    "ReportConflict",
    "ReportFact",
    "ReportFinding",
    "ReportRiskFlag",
    "ReportSection",
    "ReportType",
    "api",
]
