"""Parser adapters.

Two pipelines share one output schema (PageElement -> ParsedChunk):
* baseline : pdfplumber (fast, reveals limitations, good tables)
* docling  : Docling (structure-aware: layout, reading order, tables, OCR)
* hybrid   : Docling structure with Baseline page/table fallback

An optional OCR adapter (pytesseract + pdf2image) is provided for scanned forms.
"""
from packages.core.parsers.base import PageElement, ParseResult, ParserAdapter, get_parser

__all__ = ["PageElement", "ParseResult", "ParserAdapter", "get_parser"]
