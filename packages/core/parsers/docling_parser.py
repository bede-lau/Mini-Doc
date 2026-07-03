"""Docling structured parser.

Docling gives layout-aware conversion: titles, paragraphs, list items, tables,
captions and reading order, with page provenance. This adapter maps Docling's
document model onto our PageElement schema. Docling's API evolves between
versions, so attribute access is defensive and degrades gracefully.
"""
from __future__ import annotations

from pathlib import Path

from packages.core.parsers.base import PageElement, ParseResult, ParserAdapter
from packages.core.schemas.chunk import ChunkType
from packages.core.schemas.document import DocumentMeta
from packages.core.utils.logging import get_logger

log = get_logger(__name__)

# Map Docling item labels to our chunk types.
_LABEL_MAP: dict[str, ChunkType] = {
    "title": "paragraph",
    "section_header": "paragraph",
    "section-header": "paragraph",
    "header": "paragraph",
    "paragraph": "paragraph",
    "text": "paragraph",
    "list_item": "list",
    "list-item": "list",
    "bullet_list": "list",
    "table": "table",
    "caption": "figure_caption",
    "picture_caption": "figure_caption",
    "page_header": "unknown",
    "page_footer": "unknown",
    "footnote": "paragraph",
}
_SKIP_LABELS = {"page_header", "page_footer", "header", "footer"}


def _first_page(item) -> int:
    """Best-effort page number (1-indexed) from a Docling item's provenance."""
    prov = getattr(item, "prov", None)
    try:
        if prov:
            first = prov[0]
            return int(getattr(first, "page_no", 0) or getattr(first, "page", 0) or 1)
    except Exception:
        pass
    return 1


def _item_text(item) -> str:
    """Extract text/markdown from a Docling item, version-tolerant."""
    # Tables export to markdown; text items expose .text.
    for method in ("export_to_markdown", "to_markdown"):
        fn = getattr(item, method, None)
        if callable(fn):
            try:
                md = fn()
                if md and md.strip():
                    return md.strip()
            except Exception:
                pass
    for attr in ("text", "label_text"):
        val = getattr(item, attr, None)
        if val and str(val).strip():
            return str(val).strip()
    return ""


class DoclingParser(ParserAdapter):
    name = "docling"

    def __init__(self) -> None:
        self._converter = None

    def _converter_obj(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter

            # Default pipeline. OCR models download on first use; see MANUAL_TASKS.
            self._converter = DocumentConverter()
        return self._converter

    def parse(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        conv = self._converter_obj()
        result = conv.convert(str(pdf_path))
        doc = getattr(result, "document", None) or result

        elements: list[PageElement] = []
        current_section: str | None = None
        last_page = 1
        empty_pages = 0
        seen_pages: set[int] = set()

        iterate = getattr(doc, "iterate_items", None) or getattr(doc, "iter_items", None)
        if iterate is None:
            return ParseResult(
                document=document,
                errors=["docling: no iterate_items API on document"],
            )

        for item in iterate():
            label = str(getattr(item, "label", "") or "").lower().strip()
            page = _first_page(item) or last_page
            last_page = page
            seen_pages.add(page)

            if label in _SKIP_LABELS:
                continue

            text = _item_text(item)
            if not text:
                continue

            mapped = _LABEL_MAP.get(label, "paragraph")

            # Headings define the running section for downstream elements.
            if label in {"title", "section_header", "section-header"} and len(text) <= 120:
                current_section = text
                # Still emit so the heading is retrievable/citable.
                elements.append(
                    PageElement(
                        page=page,
                        element_type=mapped,
                        text=text,
                        section_heading=current_section,
                    )
                )
                continue

            elements.append(
                PageElement(
                    page=page,
                    element_type=mapped,
                    text=text,
                    section_heading=current_section,
                )
            )

        page_count = max(seen_pages) if seen_pages else int(getattr(doc, "num_pages", 0) or 0)

        # Crude empty-page detection: pages in range with no elements.
        if page_count:
            empty_pages = len(set(range(1, page_count + 1)) - seen_pages)

        return ParseResult(
            document=document,
            elements=elements,
            page_count=page_count,
            empty_pages=empty_pages,
        )
