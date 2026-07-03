"""Parser adapter interface and shared result types.

A parser turns a PDF into a flat list of page-level PageElements. The chunker
then segments those elements into ParsedChunks. Keeping extraction and
segmentation separate means a parser never needs to know chunk sizes, and the
chunker never needs to know how text was extracted.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from packages.core.schemas.chunk import ChunkType
from packages.core.schemas.document import DocumentMeta
from packages.core.utils.logging import get_logger
from packages.core.utils.timeutil import now_iso

log = get_logger(__name__)


class PageElement(BaseModel):
    """One addressable block of content on a page (paragraph, table, etc.)."""

    page: int
    element_type: ChunkType
    text: str
    section_heading: str | None = None
    bbox: list[float] | None = None


class ParseResult(BaseModel):
    document: DocumentMeta
    elements: list[PageElement] = Field(default_factory=list)
    page_count: int = 0
    empty_pages: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
    crashed: bool = False

    @property
    def latency_per_page(self) -> float:
        return self.elapsed_seconds / self.page_count if self.page_count else 0.0


class ParserAdapter(ABC):
    """Base class for all parser adapters."""

    name: ClassVar[str] = "base"

    @abstractmethod
    def parse(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        """Extract PageElements from a PDF."""

    # Convenience wrapper that times the parse and finalises document metadata.
    def run(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        start = time.perf_counter()
        try:
            result = self.parse(pdf_path, document)
        except Exception as exc:  # never let one bad PDF crash the pipeline
            log.exception("parser %s crashed on %s", self.name, pdf_path)
            elapsed = time.perf_counter() - start
            return ParseResult(
                document=document.model_copy(
                    update={
                        "parse_status": "failed",
                        "parser": self.name,  # type: ignore[arg-type]
                        "errors": [*document.errors, f"crash: {exc}"],
                    }
                ),
                crashed=True,
                elapsed_seconds=elapsed,
                errors=[f"crash: {exc}"],
            )
        elapsed = time.perf_counter() - start
        result.elapsed_seconds = result.elapsed_seconds or elapsed
        status = "success" if not result.errors else "partial"
        if result.crashed:
            status = "failed"
        result.document = result.document.model_copy(
            update={
                "parser": self.name,  # type: ignore[arg-type]
                "page_count": result.page_count or result.document.page_count,
                "parse_status": status,  # type: ignore[arg-type]
                "parse_completed_at": now_iso(),
                "errors": result.errors,
            }
        )
        return result


def get_parser(name: str) -> ParserAdapter:
    """Factory; imports lazily so the heavy parser deps are optional."""
    if name == "baseline":
        from packages.core.parsers.baseline import BaselineParser

        return BaselineParser()
    if name == "docling":
        from packages.core.parsers.docling_parser import DoclingParser

        return DoclingParser()
    if name == "ocr":
        from packages.core.parsers.ocr import OCRParser

        return OCRParser()
    raise ValueError(f"unknown parser: {name!r}")
