"""Document lifecycle routes: ingest, list, parse, index."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from packages.core.config import get_settings
from packages.core.pipeline import index_document_chunks, parse_and_persist
from packages.core.schemas.api import (
    DocumentListResponse,
    IndexRequest,
    IndexResponse,
    IngestResponse,
    ParseRequest,
    ParseResponse,
)
from packages.core.schemas.document import DocumentMeta
from packages.core.utils.hashing import sha256_file
from packages.core.utils.logging import get_logger
from services.api.state import get_registry
from scripts.common import ensure_data_dirs as _ensure_data_dirs, manifest_index as _manifest_index

log = get_logger(__name__)
router = APIRouter(tags=["documents"])


def _quick_page_count(path) -> int:
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            return len(pdf.pages)
    except Exception as exc:
        log.warning("page count probe failed for %s: %s", path, exc)
        return 0


MAX_UPLOAD_BYTES = 60 * 1024 * 1024  # 60 MB upload cap


def _safe_name(name: str | None) -> str:
    """Reduce a client-supplied filename to a bare basename, rejecting traversal."""
    raw = (name or "").strip()
    base = os.path.basename(raw)
    if base in ("", ".", "..") or base != raw or "/" in raw or "\\" in raw:
        raise HTTPException(status_code=400, detail="invalid filename")
    return base


def _resolve_within(name: str, base_dir: Path) -> Path:
    """Resolve name under base_dir, refusing anything that escapes it."""
    p = (base_dir / name).resolve()
    if not p.is_relative_to(base_dir.resolve()):
        raise HTTPException(status_code=400, detail="path escapes raw_docs")
    return p


def _stream_upload(src, dest: Path) -> None:
    """Stream an upload to disk in 1 MiB chunks, aborting past the size cap."""
    written = 0
    with dest.open("wb") as fh:
        while True:
            block = src.read(1 << 20)
            if not block:
                break
            written += len(block)
            if written > MAX_UPLOAD_BYTES:
                fh.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="upload too large")
            fh.write(block)


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    file: UploadFile | None = File(None),
    filename: str | None = Form(None),
) -> IngestResponse:
    s = get_settings()
    _ensure_data_dirs(s)
    if file is not None:
        name = _safe_name(file.filename)
        path = _resolve_within(name, s.raw_docs_dir)
        _stream_upload(file.file, path)
    elif filename:
        name = _safe_name(filename)
        path = _resolve_within(name, s.raw_docs_dir)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"not in raw_docs: {name}")
    else:
        raise HTTPException(status_code=400, detail="provide a 'file' upload or a 'filename'.")

    sha = sha256_file(path)
    page_count = _quick_page_count(path)
    mindex = _manifest_index()
    meta = mindex.get(path.name, {})
    registry = get_registry()
    doc = DocumentMeta(
        document_id=sha[:16],
        filename=path.name,
        domain=meta.get("domain", "unknown"),
        document_type=meta.get("document_type", "unknown"),
        source_url=meta.get("source_url") or None,
        page_count=page_count,
        parser="baseline",
        parse_status="success" if page_count else "pending",  # type: ignore[arg-type]
        sha256=sha,
    )
    registry.upsert(doc)
    return IngestResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        page_count=page_count,
        parser="baseline",
        status=doc.parse_status,  # type: ignore[arg-type]
        sha256=sha,
        errors=[],
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    docs = get_registry().list()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    s = get_settings()
    registry = get_registry()
    if req.document_ids:
        docs = [d for d in (registry.get(i) for i in req.document_ids) if d]
    else:
        docs = registry.list()

    processed = succeeded = failed = total_chunks = 0
    errors: list[str] = []
    for doc in docs:
        try:
            outcome = parse_and_persist(doc, req.parser, s, registry)
            processed += 1
            total_chunks += len(outcome["chunks"])
            if outcome["crashed"] or outcome["document"].parse_status == "failed":
                failed += 1
                errors.extend(outcome["errors"])
            else:
                succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{doc.filename}: {exc}")
            log.exception("parse failed for %s", doc.filename)
    return ParseResponse(
        parser=req.parser,
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        chunks=total_chunks,
        errors=errors,
    )


@router.post("/index", response_model=IndexResponse)
def index(req: IndexRequest) -> IndexResponse:
    s = get_settings()
    parsers = ["docling", "baseline"] if req.parser == "any" else [req.parser]
    total = 0
    errors: list[str] = []
    for p in parsers:
        try:
            total += index_document_chunks(p, req.document_ids, s)
        except Exception as exc:
            errors.append(f"{p}: {exc}")
            log.exception("index failed for parser=%s", p)
    status = "failed" if errors and total == 0 else ("partial" if errors else "success")
    return IndexResponse(
        indexed_chunks=total,
        collection=s.qdrant_collection,
        vector_dim=s.embedding_dim,
        status=status,  # type: ignore[arg-type]
        errors=errors,
    )
