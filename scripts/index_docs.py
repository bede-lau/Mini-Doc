"""Index parsed chunks into Qdrant.

Usage:
    python scripts/index_docs.py --parser docling
    python scripts/index_docs.py --parser any [--document-ids <id,...>]

Requires Qdrant running: docker compose up -d qdrant
"""
from __future__ import annotations

import argparse

from common import bootstrap

bootstrap()
from packages.core.config import get_settings  # noqa: E402
from packages.core.retrieval.embeddings import Embedder  # noqa: E402
from packages.core.retrieval.qdrant_store import QdrantStore, store_available  # noqa: E402
from packages.core.schemas.chunk import ParsedChunk  # noqa: E402
from packages.core.utils.logging import get_logger  # noqa: E402

log = get_logger("index")


def _iter_chunks(parser_dir, document_ids):
    if not parser_dir.exists():
        return
    for f in sorted(parser_dir.glob("*.jsonl")):
        doc_id = f.stem
        if document_ids and doc_id not in document_ids:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                yield ParsedChunk.model_validate_json(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", choices=["baseline", "docling", "ocr", "any"], default="docling")
    ap.add_argument("--document-ids", help="comma-separated document_ids")
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()

    s = get_settings()
    if not store_available(s):
        log.error("Qdrant not reachable at %s. Start it: docker compose up -d qdrant", s.qdrant_url)
        return 1

    document_ids = set(args.document_ids.split(",")) if args.document_ids else None
    parser_dirs = [s.chunks_dir / args.parser] if args.parser != "any" else [
        s.chunks_dir / "docling", s.chunks_dir / "baseline", s.chunks_dir / "ocr"
    ]

    embedder = Embedder(s)
    store = QdrantStore(s)
    store.ensure_collection()

    total = 0
    for d in parser_dirs:
        batch_chunks: list[ParsedChunk] = []
        for chunk in _iter_chunks(d, document_ids):
            batch_chunks.append(chunk)
            if len(batch_chunks) >= args.batch:
                vecs = embedder.encode([c.chunk_text for c in batch_chunks])
                total += store.upsert_chunks(batch_chunks, vecs)
                batch_chunks.clear()
                log.info("indexed %d chunks so far (dir=%s)", total, d.name)
        if batch_chunks:
            vecs = embedder.encode([c.chunk_text for c in batch_chunks])
            total += store.upsert_chunks(batch_chunks, vecs)

    count = store.count()
    print(f"\nindexed={total} new points | collection={s.qdrant_collection} | total_points={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
