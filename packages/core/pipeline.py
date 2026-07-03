"""Pipeline orchestration shared by CLI scripts and the FastAPI service.

Keeps the parse -> persist -> chunk sequence in one place so the API and the
scripts stay consistent.
"""
from __future__ import annotations

import json

from packages.core.chunking import Chunker
from packages.core.config import Settings, get_settings
from packages.core.parsers.base import get_parser
from packages.core.registry import DocumentRegistry
from packages.core.schemas.chunk import ParsedChunk
from packages.core.schemas.document import DocumentMeta
from packages.core.utils.logging import get_logger
from packages.core.utils.timeutil import now_iso

log = get_logger(__name__)


def parse_and_persist(
    doc: DocumentMeta,
    parser_name: str,
    settings: Settings | None = None,
    registry: DocumentRegistry | None = None,
) -> dict:
    """Parse one document, persist elements + chunks, update the registry.

    Returns a dict with the updated document, chunks, page_count, empty_pages,
    crashed flag and errors. Safe to call repeatedly per (doc, parser).
    """
    s = settings or get_settings()
    reg = registry or DocumentRegistry(settings=s)

    pdf_path = s.raw_docs_dir / doc.filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"raw PDF not found: {pdf_path}")

    doc = reg.upsert(doc.merge(parse_started_at=now_iso()))
    result = get_parser(parser_name).run(pdf_path, doc)

    parsed_dir = s.parsed_dir / parser_name
    chunks_dir = s.chunks_dir / parser_name
    parsed_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    (parsed_dir / f"{doc.document_id}_parsed.json").write_text(
        json.dumps(result.model_dump(), indent=2), encoding="utf-8"
    )

    chunks: list[ParsedChunk] = Chunker(s).chunk(result)
    with (chunks_dir / f"{doc.document_id}.jsonl").open("w", encoding="utf-8") as cf:
        for ch in chunks:
            cf.write(ch.model_dump_json() + "\n")

    reg.upsert(result.document)

    with (s.parsed_dir / "_parse_metrics.jsonl").open("a", encoding="utf-8") as mf:
        mf.write(json.dumps({
            "document_id": doc.document_id,
            "filename": doc.filename,
            "parser": parser_name,
            "page_count": result.page_count,
            "empty_pages": result.empty_pages,
            "elapsed_seconds": round(result.elapsed_seconds, 4),
            "crashed": result.crashed,
            "errors_count": len(result.errors),
            "chunk_count": len(chunks),
            "ts": now_iso(),
        }) + "\n")

    return {
        "document": result.document,
        "chunks": chunks,
        "page_count": result.page_count,
        "empty_pages": result.empty_pages,
        "crashed": result.crashed,
        "errors": result.errors,
    }


def index_document_chunks(
    parser_name: str,
    document_ids: list[str] | None,
    settings: Settings | None = None,
    batch: int = 64,
) -> int:
    """Index chunk JSONL for the given parser into Qdrant. Returns points upserted."""
    from packages.core.retrieval.embeddings import Embedder
    from packages.core.retrieval.qdrant_store import QdrantStore

    s = settings or get_settings()
    parser_dir = s.chunks_dir / parser_name
    wanted = set(document_ids) if document_ids else None
    embedder = Embedder(s)
    store = QdrantStore(s)
    store.ensure_collection()

    total = 0
    buffer: list[ParsedChunk] = []
    if parser_dir.exists():
        for f in sorted(parser_dir.glob("*.jsonl")):
            if wanted and f.stem not in wanted:
                continue
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                buffer.append(ParsedChunk.model_validate_json(line))
                if len(buffer) >= batch:
                    total += store.upsert_chunks(buffer, embedder.encode([c.chunk_text for c in buffer]))
                    buffer.clear()
    if buffer:
        total += store.upsert_chunks(buffer, embedder.encode([c.chunk_text for c in buffer]))
    return total
