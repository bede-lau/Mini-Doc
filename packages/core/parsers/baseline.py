"""Baseline parser using pdfplumber.

Fast text + table extraction. Deliberately "dumb" reading order; this reveals
the limitations that the Docling parser is meant to overcome (a key comparison
in the benchmark).
"""
from __future__ import annotations

import re
from pathlib import Path

from packages.core.parsers.base import PageElement, ParseResult, ParserAdapter
from packages.core.schemas.document import DocumentMeta
from packages.core.utils.logging import get_logger

log = get_logger(__name__)

_HEADING_PATTERNS = [
    re.compile(r"^\d+(\.\d+)*\s+\S"),          # 1. / 1.2 / 3.1.4 Title
    re.compile(r"^(?:section|appendix|chapter|part|article)\b", re.I),
    re.compile(r"^[A-Z0-9][A-Z0-9 .,&'/-]{2,80}$"),  # ALL-CAPS / Title-ish line
]


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not (3 <= len(s) <= 90):
        return False
    if s.endswith((".", ":", ";", ",")):
        return False
    if any(p.search(s) for p in _HEADING_PATTERNS):
        # Avoid false positives like normal sentences in caps.
        if not s.isupper() and not re.match(r"^\d", s):
            return False
        return True
    return False


def _split_paragraphs(text: str) -> list[str]:
    # Collapse whitespace and split on blank-line boundaries.
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [re.sub(r"\s+", " ", p).strip() for p in paragraphs if p.strip()]


def _table_to_text(table: list[list]) -> str:
    rows = []
    for row in table or []:
        cells = ["" if c is None else str(c).replace("\n", " ").strip() for c in row]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


class BaselineParser(ParserAdapter):
    name = "baseline"

    def parse(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        import pdfplumber  # lazy: keeps test/import light

        elements: list[PageElement] = []
        errors: list[str] = []
        empty_pages = 0
        page_count = 0

        with pdfplumber.open(str(pdf_path)) as pdf:
            page_count = len(pdf.pages)
            # Running section heading persists across pages (consistent with docling).
            current_section: str | None = None
            for idx, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    tables = page.extract_tables() or []
                except Exception as exc:  # per-page resilience
                    errors.append(f"page {idx}: {exc}")
                    text, tables = "", []

                # Maintain a running section heading from detected heading lines.
                page_has_content = False

                # Tables first so their text isn't double counted with raw text.
                for tbl in tables:
                    ttext = _table_to_text(tbl)
                    if ttext.strip():
                        page_has_content = True
                        elements.append(
                            PageElement(
                                page=idx,
                                element_type="table",
                                text=ttext,
                                section_heading=current_section,
                            )
                        )

                # Segment text into paragraphs, tracking headings.
                for para in _split_paragraphs(text):
                    first_line = para.split(". ", 1)[0]
                    if _is_heading(first_line) and len(para) < 120:
                        current_section = para
                        continue
                    page_has_content = True
                    elements.append(
                        PageElement(
                            page=idx,
                            element_type="paragraph",
                            text=para,
                            section_heading=current_section,
                        )
                    )

                if not page_has_content:
                    empty_pages += 1

        if page_count == 0:
            errors.append("pdf has 0 pages")

        return ParseResult(
            document=document,
            elements=elements,
            page_count=page_count,
            empty_pages=empty_pages,
            errors=errors,
        )
