"""Parse raw PDFs into chunks (hybrid, baseline, or docling).

Usage:
python scripts/parse_docs.py --parser hybrid
python scripts/parse_docs.py --parser docling [--document-ids <id,...>] [--force]

Registers any unregistered raw PDF (using the manifest for metadata), parses it
with the selected parser, writes element JSON + chunk JSONL, updates the
registry, and appends per-document parse metrics used by the benchmark.
"""
from __future__ import annotations

import argparse

from common import bootstrap, ensure_data_dirs, manifest_index

bootstrap()
from packages.core.config import get_settings  # noqa: E402
from packages.core.pipeline import parse_and_persist  # noqa: E402
from packages.core.registry import DocumentRegistry  # noqa: E402
from packages.core.schemas.document import DocumentMeta  # noqa: E402
from packages.core.utils.hashing import sha256_file  # noqa: E402
from packages.core.utils.logging import get_logger  # noqa: E402

log = get_logger("parse")


def _register_raw(filename: str, registry: DocumentRegistry, mindex: dict) -> DocumentMeta | None:
    s = get_settings()
    path = s.raw_docs_dir / filename
    if not path.exists():
        log.warning("raw PDF missing, skipping: %s", filename)
        return None
    existing = registry.by_filename(filename)
    if existing:
        return existing
    meta = mindex.get(filename, {})
    return registry.upsert(DocumentMeta(
        document_id=sha256_file(path)[:16],
        filename=filename,
        domain=meta.get("domain", "unknown"),
        document_type=meta.get("document_type", "unknown"),
        source_url=meta.get("source_url") or None,
        sha256=sha256_file(path),
    ))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", choices=["baseline", "docling", "hybrid"], default="hybrid")
    ap.add_argument("--document-ids", help="comma-separated document_ids (default: all)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    ensure_data_dirs(s)
    registry = DocumentRegistry(settings=s)
    mindex = manifest_index()

    if args.document_ids:
        wanted = [d for d in registry.list() if d.document_id in args.document_ids.split(",")]
    else:
        wanted = []
        for row in mindex.values():
            doc = _register_raw(row["filename"], registry, mindex)
            if doc:
                wanted.append(registry.by_filename(row["filename"]))
        known = {d.document_id for d in wanted}
        for d in registry.list():
            if d.document_id not in known:
                wanted.append(d)

    processed = succeeded = failed = total_chunks = 0
    for doc in wanted:
        pdf_path = s.raw_docs_dir / doc.filename
        if not pdf_path.exists():
            log.warning("missing PDF for %s, skipping", doc.filename)
            continue
        outcome = parse_and_persist(doc, args.parser, s, registry)
        processed += 1
        if outcome["crashed"] or outcome["document"].parse_status == "failed":
            failed += 1
        else:
            succeeded += 1
        total_chunks += len(outcome["chunks"])
        log.info(
            "%-45s pages=%-3s chunks=%-4s status=%s",
            doc.filename, outcome["page_count"], len(outcome["chunks"]), outcome["document"].parse_status,
        )

    print(
        f"\nparser={args.parser} processed={processed} succeeded={succeeded} "
        f"failed={failed} chunks={total_chunks}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
