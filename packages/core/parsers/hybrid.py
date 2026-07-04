"""Strict hybrid parser combining Docling structure with Baseline resilience.

Merge policy:
* Docling owns page reading order, headings, lists, captions and layout-aware text
  when a page has credible Docling output.
* Baseline owns a page when Docling is empty/weak for that page.
* Baseline tables are preserved when Docling has no table for the page, or when
  Baseline extracted materially more table text.
* Exact/near-exact duplicate elements are suppressed.

The parser is intentionally deterministic: each page is adjudicated with local
evidence only, every fallback is reported in ``errors``, and no page is silently
dropped when Baseline has recoverable content.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from packages.core.parsers.base import PageElement, ParseResult, ParserAdapter
from packages.core.parsers.baseline import BaselineParser
from packages.core.parsers.docling_parser import DoclingParser
from packages.core.schemas.document import DocumentMeta

_MIN_DOCLING_PAGE_CHARS = 40
_TABLE_REPLACE_RATIO = 1.15
_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s|.-]+", re.UNICODE)


def _norm(text: str) -> str:
    """Stable, strict-enough key for duplicate suppression."""
    return _WS.sub(" ", _PUNCT.sub("", text.lower())).strip()


def _by_page(elements: list[PageElement]) -> dict[int, list[PageElement]]:
    pages: dict[int, list[PageElement]] = defaultdict(list)
    for el in elements:
        pages[max(1, int(el.page))].append(el)
    return dict(pages)


def _text_len(elements: list[PageElement], *, include_tables: bool = True) -> int:
    return sum(
        len(el.text.strip())
        for el in elements
        if include_tables or el.element_type != "table"
    )


def _table_len(elements: list[PageElement]) -> int:
    return _text_len([el for el in elements if el.element_type == "table"])


def _dedupe(elements: list[PageElement]) -> list[PageElement]:
    seen: set[tuple[str, str]] = set()
    out: list[PageElement] = []
    for el in elements:
        key = (el.element_type, _norm(el.text))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        out.append(el)
    return out


def _mark(el: PageElement, source_parser: str, fallback_reason: str | None = None) -> PageElement:
    return el.model_copy(
        update={
            "source_parser": source_parser,
            "fallback_reason": fallback_reason,
        }
    )


def _mark_many(
    elements: list[PageElement],
    source_parser: str,
    fallback_reason: str | None = None,
) -> list[PageElement]:
    return [_mark(el, source_parser, fallback_reason) for el in elements]


def merge_results(docling: ParseResult, baseline: ParseResult) -> tuple[list[PageElement], list[str]]:
    """Merge two parser outputs with deterministic per-page rules.

    Returns merged elements plus audit messages describing every fallback or
    table substitution. Public for unit tests; callers still use HybridParser.
    """
    errors: list[str] = []
    d_pages = _by_page(docling.elements)
    b_pages = _by_page(baseline.elements)
    page_count = max(docling.page_count, baseline.page_count, *d_pages.keys(), *b_pages.keys(), 0)
    merged: list[PageElement] = []

    for page in range(1, page_count + 1):
        d_els = d_pages.get(page, [])
        b_els = b_pages.get(page, [])
        d_has_table = any(el.element_type == "table" for el in d_els)
        d_non_table_chars = _text_len(d_els, include_tables=False)
        b_chars = _text_len(b_els)

        docling_is_weak = bool(b_els) and (
            not d_els
            or (
                not d_has_table
                and d_non_table_chars < _MIN_DOCLING_PAGE_CHARS
                and b_chars > d_non_table_chars
            )
        )

        if docling_is_weak:
            reason = "docling output was weak/empty"
            merged.extend(_mark_many(b_els, "baseline", reason))
            errors.append(f"hybrid page {page}: used baseline because {reason}")
            continue

        page_out = _mark_many(d_els, "docling")
        d_table_chars = _table_len(d_els)
        b_table_chars = _table_len(b_els)
        b_tables = [el for el in b_els if el.element_type == "table"]

        if b_tables and (d_table_chars == 0 or b_table_chars > d_table_chars * _TABLE_REPLACE_RATIO):
            page_out = [el for el in page_out if el.element_type != "table"]
            reason = "missing docling table" if d_table_chars == 0 else "richer baseline table"
            page_out.extend(_mark_many(b_tables, "baseline", reason))
            errors.append(f"hybrid page {page}: used baseline table extraction ({reason})")

        merged.extend(_dedupe(page_out))

    return merged, errors


class HybridParser(ParserAdapter):
    """Per-page/element merge of Docling and Baseline parser outputs."""

    name = "hybrid"

    def __init__(self) -> None:
        # Windowed docling: dodges ``std::bad_alloc`` on long reports; per-page
        # baseline merge below still fills any weak/empty docling pages.
        self.docling = DoclingParser(backfill_with_baseline=False, window_size=8)
        self.baseline = BaselineParser()

    def parse(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        baseline = self.baseline.run(pdf_path, document)
        docling = self.docling.run(pdf_path, document)

        elements, merge_audit = merge_results(docling, baseline)
        page_count = max(docling.page_count, baseline.page_count)
        pages_with_content = {el.page for el in elements if el.text.strip()}
        empty_pages = len(set(range(1, page_count + 1)) - pages_with_content) if page_count else 0
        # Real errors = upstream parser errors only. The merge audit trail
        # (per-page baseline fallbacks, table substitutions) is informational
        # and goes to ``audit`` so it does not flip the doc to "partial".
        errors = [*docling.errors, *baseline.errors]

        return ParseResult(
            document=document,
            elements=elements,
            page_count=page_count,
            empty_pages=empty_pages,
            errors=errors,
            audit=merge_audit,
            crashed=baseline.crashed and docling.crashed,
        )
