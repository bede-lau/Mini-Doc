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


def _unwrap_item(raw):
    """Docling 2.x may yield either item or (item, level) from iterate_items."""
    if isinstance(raw, (tuple, list)) and raw:
        return raw[0]
    return raw


def _label_value(item) -> str:
    """Return a stable lower-case label from Docling enum/string labels."""
    label = getattr(item, "label", "") or ""
    label = getattr(label, "value", label)
    return str(label).lower().strip()


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


def _page_count(doc, seen_pages: set[int]) -> int:
    num_pages = getattr(doc, "num_pages", None)
    if callable(num_pages):
        try:
            return int(num_pages() or 0)
        except Exception:
            pass
    if num_pages:
        try:
            return int(num_pages)
        except Exception:
            pass
    pages = getattr(doc, "pages", None)
    if pages is not None:
        try:
            return len(pages)
        except Exception:
            pass
    return max(seen_pages) if seen_pages else 0


class DoclingParser(ParserAdapter):
    name = "docling"

    # When set, the PDF is converted in fixed-size page windows instead of one
    # ``convert()`` call. docling-parse holds per-page bitmaps in native (C++)
    # memory during preprocessing; on long reports a single convert exhausts the
    # allocator and every page past the exhaustion point fails with
    # ``std::bad_alloc`` (contiguous-tail failure). A fresh converter per window
    # resets the native allocator between windows. ``None`` keeps the legacy
    # single-shot path (fine for small PDFs, and used by unit tests that patch
    # the cached converter).
    DEFAULT_WINDOW_SIZE: int | None = None

    def __init__(
        self,
        *,
        backfill_with_baseline: bool = False,
        window_size: int | None = DEFAULT_WINDOW_SIZE,
    ) -> None:
        self._converter = None
        self.backfill_with_baseline = backfill_with_baseline
        self.window_size = window_size

    def _build_converter(self):
        """Construct a fresh DocumentConverter with CPU-friendly options."""
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter
        from docling.document_converter import PdfFormatOption

        # Use Docling's structured PDF parser, but keep the local demo path
        # lightweight and deterministic. The public PDFs contain embedded
        # text; enabling OCR on large annual reports can exhaust memory on
        # Windows CPU-only runs before yielding any chunks.
        opts = PdfPipelineOptions()
        opts.do_ocr = False
        opts.ocr_batch_size = 1
        opts.layout_batch_size = 1
        opts.table_batch_size = 1
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
            }
        )

    def _converter_obj(self):
        # Cached converter for the legacy single-shot path. The windowed path
        # bypasses this and calls ``_build_converter`` per window instead.
        if self._converter is None:
            self._converter = self._build_converter()
        return self._converter

    def _baseline_result(self, pdf_path: Path, document: DocumentMeta, reason: str) -> ParseResult:
        """Recover with Baseline when Docling exhausts memory or drops pages."""
        from packages.core.parsers.baseline import BaselineParser

        result = BaselineParser().parse(pdf_path, document)
        result.errors = [f"docling fallback: {reason}", *result.errors]
        return result

    def _pdf_page_count(self, pdf_path: Path) -> int:
        """Page count via pypdf (separate method so tests can override)."""
        from pypdf import PdfReader

        return len(PdfReader(str(pdf_path)).pages)

    def _split_pdf_window(self, pdf_path: Path, start: int, end: int, tmp_dir: Path) -> Path:
        """Write pages [start, end] (1-indexed, inclusive) to a standalone PDF.

        docling's public ``convert()`` takes a whole file and exposes no page
        range, so we materialise a windowed sub-PDF with pypdf and convert that.
        """
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        for i in range(start - 1, min(end, len(reader.pages))):
            writer.add_page(reader.pages[i])
        out = tmp_dir / f"pages_{start:04d}_{end:04d}.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return out

    def _extract_elements(
        self, doc, page_offset: int = 0
    ) -> tuple[list[PageElement], set[int], list[str]]:
        """Pull PageElements from a Docling doc.

        ``page_offset`` shifts window-local page numbers back to document space
        (used by the windowed path; 0 for the single-shot path).
        """
        elements: list[PageElement] = []
        seen_pages: set[int] = set()
        errors: list[str] = []

        iterate = getattr(doc, "iterate_items", None) or getattr(doc, "iter_items", None)
        if iterate is None:
            return elements, seen_pages, ["docling: no iterate_items API on document"]

        current_section: str | None = None
        last_page = 1
        for raw_item in iterate():
            item = _unwrap_item(raw_item)
            label = _label_value(item)
            local_page = _first_page(item) or last_page
            last_page = local_page
            page = local_page + page_offset
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
        return elements, seen_pages, errors

    def _apply_baseline_backfill(
        self, parsed: ParseResult, pdf_path: Path, document: DocumentMeta
    ) -> ParseResult:
        """Fill pages with no Docling elements using the resilient Baseline parser."""
        baseline = self._baseline_result(
            pdf_path,
            document,
            f"backfilled {parsed.empty_pages} empty/failed docling pages",
        )
        baseline_by_page = {page: [] for page in range(1, baseline.page_count + 1)}
        for el in baseline.elements:
            baseline_by_page.setdefault(el.page, []).append(el)
        docling_pages = {el.page for el in parsed.elements if el.text.strip()}
        backfilled: list[PageElement] = []
        for page in range(1, max(parsed.page_count, baseline.page_count) + 1):
            if page in docling_pages:
                backfilled.extend([el for el in parsed.elements if el.page == page])
            else:
                replacement = baseline_by_page.get(page, [])
                if replacement:
                    backfilled.extend(replacement)
        if len(backfilled) > len(parsed.elements):
            parsed.elements = backfilled
            parsed.page_count = max(parsed.page_count, baseline.page_count)
            pages_with_content = {el.page for el in parsed.elements if el.text.strip()}
            parsed.empty_pages = (
                len(set(range(1, parsed.page_count + 1)) - pages_with_content)
                if parsed.page_count
                else 0
            )
            parsed.errors = [
                *parsed.errors,
                "docling fallback: baseline backfilled pages without docling elements",
            ]
        return parsed

    def parse(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        if self.window_size:
            return self._parse_windowed(pdf_path, document)
        return self._parse_single(pdf_path, document)

    def _parse_single(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        """Legacy single-shot convert path (whole PDF in one ``convert()`` call)."""
        conv = self._converter_obj()
        try:
            result = conv.convert(str(pdf_path))
        except Exception as exc:
            # Docling can surface native allocation failures as RuntimeError or
            # generic extension exceptions (e.g. ``std::bad_alloc`` on Windows
            # CPU preprocessing). Keep the document parseable for the demo by
            # falling back to the resilient Baseline parser instead of returning
            # zero chunks.
            if self.backfill_with_baseline:
                return self._baseline_result(pdf_path, document, f"conversion failed: {exc}")
            raise
        doc = getattr(result, "document", None) or result

        elements, seen_pages, errors = self._extract_elements(doc)
        page_count = _page_count(doc, seen_pages)
        empty_pages = (
            len(set(range(1, page_count + 1)) - seen_pages) if page_count else 0
        )

        parsed = ParseResult(
            document=document,
            elements=elements,
            page_count=page_count,
            empty_pages=empty_pages,
            errors=errors,
        )

        if self.backfill_with_baseline and page_count and empty_pages:
            parsed = self._apply_baseline_backfill(parsed, pdf_path, document)

        return parsed

    def _parse_windowed(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        """Convert the PDF in fixed-size page windows.

        Each window runs in a freshly built ``DocumentConverter`` so the
        docling-parse native allocator resets between windows, avoiding the
        ``std::bad_alloc`` tail failure seen on long reports. Page numbers are
        shifted back to document space. A failed window is recorded and skipped;
        if baseline backfill is enabled, the gaps are filled afterwards.
        """
        import tempfile

        try:
            total_pages = self._pdf_page_count(pdf_path)
        except Exception as exc:
            log.warning("windowed docling: cannot read page count (%s); single-shot", exc)
            return self._parse_single(pdf_path, document)

        window = max(1, int(self.window_size or 1))
        elements: list[PageElement] = []
        seen_pages: set[int] = set()
        errors: list[str] = []

        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)
            for start in range(1, total_pages + 1, window):
                end = min(start + window - 1, total_pages)
                try:
                    sub_path = self._split_pdf_window(pdf_path, start, end, tmp_dir)
                    conv = self._build_converter()
                    result = conv.convert(str(sub_path))
                except Exception as exc:
                    errors.append(f"docling window {start}-{end} failed: {exc}")
                    continue
                doc = getattr(result, "document", None) or result
                win_elements, win_seen, win_errors = self._extract_elements(
                    doc, page_offset=start - 1
                )
                elements.extend(win_elements)
                seen_pages.update(win_seen)
                errors.extend(win_errors)

        page_count = total_pages
        empty_pages = (
            len(set(range(1, page_count + 1)) - seen_pages) if page_count else 0
        )

        parsed = ParseResult(
            document=document,
            elements=elements,
            page_count=page_count,
            empty_pages=empty_pages,
            errors=errors,
        )

        if self.backfill_with_baseline and page_count and empty_pages:
            parsed = self._apply_baseline_backfill(parsed, pdf_path, document)

        return parsed
