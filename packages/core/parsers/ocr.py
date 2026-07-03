"""Optional OCR parser for scanned documents (e.g. FUNSD forms).

Uses Tesseract via pytesseract + pdf2image. Disabled by default and only
required for the scanned-forms stretch goal. Chunk-level metadata marks
`ocr=True` so OCR-derived content is always identifiable downstream.
"""
from __future__ import annotations

from pathlib import Path

from packages.core.parsers.base import PageElement, ParseResult, ParserAdapter
from packages.core.schemas.document import DocumentMeta

_DPI = 300


class OCRParser(ParserAdapter):
    name = "ocr"

    def parse(self, pdf_path: Path, document: DocumentMeta) -> ParseResult:
        try:
            import pytesseract  # type: ignore
            from pdf2image import convert_from_path  # type: ignore
        except ImportError as exc:
            return ParseResult(
                document=document,
                errors=[
                    "OCR requires 'pytesseract' and 'pdf2image' plus a Tesseract "
                    "binary on PATH. See MANUAL_TASKS.md. " + str(exc)
                ],
                crashed=True,
            )

        images = convert_from_path(str(pdf_path), dpi=_DPI)
        elements: list[PageElement] = []
        empty = 0
        for idx, img in enumerate(images, start=1):
            text = (pytesseract.image_to_string(img) or "").strip()
            if text:
                elements.append(
                    PageElement(
                        page=idx,
                        element_type="ocr",
                        text=text,
                        section_heading=None,
                    )
                )
            else:
                empty += 1
        return ParseResult(
            document=document,
            elements=elements,
            page_count=len(images),
            empty_pages=empty,
        )
