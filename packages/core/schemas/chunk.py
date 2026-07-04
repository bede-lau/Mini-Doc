"""The canonical chunk schema.

This is the unit of retrieval, citation, and provenance. It is produced by the
parsers, persisted as JSONL, embedded, and stored in Qdrant. Page and section
metadata are mandatory because every citation must name a filename and page.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ChunkType = Literal["paragraph", "table", "list", "figure_caption", "ocr", "unknown"]
ParserName = Literal["baseline", "docling", "hybrid", "ocr"]


class ParsedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_start: int
    page_end: int
    section_heading: str | None = None
    chunk_text: str
    chunk_type: ChunkType = "paragraph"
    bbox: list[float] | None = None
    parser: ParserName = "baseline"
    source_parser: ParserName | None = None
    fallback_reason: str | None = None
    ocr: bool = False
    token_count: int = 0
    source_url: str | None = None

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def _coerce(self) -> "ParsedChunk":
        # page_end must not precede page_start; coerce defensively.
        if self.page_end < self.page_start:
            self.page_end = self.page_start
        return self

    def to_payload(self) -> dict:
        """Dict form suitable for Qdrant payload storage."""
        return self.model_dump()

    @staticmethod
    def make_chunk_id(document_id: str, page_start: int, index: int, parser: str = "x") -> str:
        # Include the parser so baseline/docling/ocr chunks for the same
        # doc/page/position do NOT collide (Qdrant point ids derive from this).
        p = parser if parser in ("baseline", "docling", "hybrid", "ocr") else "x"
        return f"{p}_{document_id}_p{page_start}_c{index:03d}"


# Backwards-friendly alias some callers may prefer.
Chunk = ParsedChunk


# Quiet unused-import linters while keeping Field imported for future validators.
_ = Field
