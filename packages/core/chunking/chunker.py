"""Chunker — turns ParseResult elements into ParsedChunks.

Rules enforced here (from the spec):
  * chunk size ~ settings.chunk_size tokens, overlap ~ settings.chunk_overlap
  * page metadata preserved (page_start / page_end)
  * section heading preserved when available
  * table chunks kept whole when they fit
  * chunks never combine across documents (one ParseResult = one document)
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from packages.core.config import Settings, get_settings
from packages.core.parsers.base import ParseResult
from packages.core.schemas.chunk import ParsedChunk
from packages.core.utils.tokens import estimate_tokens

_SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\n+")


def _sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p and p.strip()]
    return parts or [text.strip()]


def _table_rows(text: str) -> list[str]:
    # Tables arrive as newline-joined "a | b" rows.
    return [r for r in (text or "").splitlines() if r.strip()]


class Chunker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()

    def chunk_element(self, element, document_id: str, filename: str, parser: str,
                      source_url: str | None, counter: list[int]) -> list[ParsedChunk]:
        # ParsedChunk.parser is a strict literal; normalise anything pre-parse
        # (e.g. "none") so the producer always emits schema-valid chunks.
        if parser not in ("baseline", "docling", "ocr"):
            parser = "baseline"
        etype = element.element_type
        units = _table_rows(element.text) if etype == "table" else _sentences(element.text)
        if not units:
            units = [element.text] if element.text else []

        chunks: list[ParsedChunk] = []
        buf: list[str] = []
        buf_tokens = 0
        overlap = self.s.chunk_overlap
        size = self.s.chunk_size

        def emit() -> None:
            if not buf:
                return
            counter[0] += 1
            text = "\n".join(buf) if etype == "table" else " ".join(buf)
            chunks.append(
                ParsedChunk(
                    chunk_id=ParsedChunk.make_chunk_id(
                        document_id, element.page, counter[0], parser
                    ),
                    document_id=document_id,
                    filename=filename,
                    page_start=element.page,
                    page_end=element.page,
                    section_heading=element.section_heading,
                    chunk_text=text,
                    chunk_type=etype,
                    bbox=element.bbox,
                    parser=parser,  # type: ignore[arg-type]
                    ocr=(etype == "ocr"),
                    token_count=max(1, estimate_tokens(text)),
                    source_url=source_url,
                )
            )

        for u in units:
            ut = max(1, estimate_tokens(u))
            if buf and buf_tokens + ut > size:
                # carry overlap from the current buffer BEFORE emitting resets it
                carry: list[str] = []
                carry_tokens = 0
                for cu in reversed(buf):
                    ct = max(1, estimate_tokens(cu))
                    if carry_tokens + ct > overlap:
                        break
                    carry.insert(0, cu)
                    carry_tokens += ct
                emit()
                buf = list(carry)
                buf_tokens = carry_tokens
            buf.append(u)
            buf_tokens += ut
        emit()
        return chunks

    def chunk(self, result: ParseResult) -> list[ParsedChunk]:
        doc = result.document
        counter = [0]
        out: list[ParsedChunk] = []
        for el in result.elements:
            out.extend(
                self.chunk_element(
                    el,
                    document_id=doc.document_id,
                    filename=doc.filename,
                    parser=doc.parser,
                    source_url=doc.source_url,
                    counter=counter,
                )
            )
        return out


def chunk_parse_result(result: ParseResult, settings: Settings | None = None) -> list[ParsedChunk]:
    return Chunker(settings).chunk(result)


def iter_chunks(results: Iterable[ParseResult], settings: Settings | None = None) -> list[ParsedChunk]:
    """Chunk many parse results; each result stays isolated (never cross-doc)."""
    chunker = Chunker(settings)
    out: list[ParsedChunk] = []
    for r in results:
        out.extend(chunker.chunk(r))
    return out
