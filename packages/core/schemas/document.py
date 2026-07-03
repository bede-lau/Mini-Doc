"""Document-level metadata."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ParseStatus = Literal["pending", "success", "failed", "partial"]


class DocumentMeta(BaseModel):
    """Provenance-rich record of one ingested document."""

    document_id: str
    filename: str
    domain: str
    document_type: str
    source_url: str | None = None
    page_count: int = 0
    parser: Literal["baseline", "docling", "ocr", "none"] = "none"
    parse_started_at: str | None = None
    parse_completed_at: str | None = None
    parse_status: ParseStatus = "pending"
    sha256: str | None = None
    errors: list[str] = Field(default_factory=list)

    def merge(self, **updates) -> "DocumentMeta":
        """Return a copy with field updates applied."""
        return self.model_copy(update=updates)
