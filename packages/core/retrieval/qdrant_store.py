"""Qdrant vector store client.

Stores ParsedChunks as points (cosine distance) with full metadata payload, so
every hit can be turned back into a citation with filename + page. Filtering
uses the same metadata fields the API exposes (domain, filename, parser, ...).
"""
from __future__ import annotations

import uuid
from pathlib import Path

from packages.core.config import Settings, get_settings
from packages.core.schemas.chunk import ParsedChunk
from packages.core.schemas.evidence import RetrievalHit
from packages.core.utils.logging import get_logger

log = get_logger(__name__)
_NAMESPACE = uuid.UUID("6f8b3c2a-1d4e-4b6a-9c2f-0e1a2b3c4d5e")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


def _to_filter(filters: dict | None):
    if not filters:
        return None
    from qdrant_client.http import models as qm

    must = []
    for k, v in filters.items():
        if v is None:
            continue
        if isinstance(v, list):
            must.append(qm.FieldCondition(key=k, match=qm.MatchAny(any=[str(x) for x in v])))
        else:
            must.append(qm.FieldCondition(key=k, match=qm.MatchValue(value=v)))
    return qm.Filter(must=must) if must else None


class QdrantStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=self.s.qdrant_url,
                api_key=self.s.qdrant_api_key,
                timeout=30,
            )
        return self._client

    def ensure_collection(self) -> None:
        from qdrant_client.http import models as qm

        cols = {c.name for c in self.client.get_collections().collections}
        if self.s.qdrant_collection not in cols:
            self.client.create_collection(
                collection_name=self.s.qdrant_collection,
                vectors_config=qm.VectorParams(size=self.s.embedding_dim, distance=qm.Distance.COSINE),
            )
            log.info("created qdrant collection %s (dim=%d)", self.s.qdrant_collection, self.s.embedding_dim)

    def upsert_chunks(self, chunks: list[ParsedChunk], vectors: list[list[float]]) -> int:
        from qdrant_client.http import models as qm

        if not chunks:
            return 0
        points = [
            qm.PointStruct(id=_point_id(c.chunk_id), vector=v, payload=c.to_payload())
            for c, v in zip(chunks, vectors, strict=True)
        ]
        # Batch to keep requests modest.
        batch = 256
        for i in range(0, len(points), batch):
            self.client.upsert(collection_name=self.s.qdrant_collection, points=points[i : i + batch])
        return len(points)

    def search(self, vector: list[float], top_k: int, filters: dict | None = None) -> list[RetrievalHit]:
        query_filter = _to_filter(filters)
        if hasattr(self.client, "search"):
            hits = self.client.search(
                collection_name=self.s.qdrant_collection,
                query_vector=vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )
        else:
            # qdrant-client >=1.18 replaced search() with query_points().
            response = self.client.query_points(
                collection_name=self.s.qdrant_collection,
                query=vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )
            hits = getattr(response, "points", response)
        out: list[RetrievalHit] = []
        for p in hits:
            payload = p.payload or {}
            out.append(
                RetrievalHit(
                    chunk_id=payload.get("chunk_id", str(p.id)),
                    document_id=payload.get("document_id", ""),
                    filename=payload.get("filename", ""),
                    page_start=int(payload.get("page_start", 0) or 0),
                    page_end=int(payload.get("page_end", 0) or payload.get("page_start", 0) or 0),
                    section=payload.get("section_heading"),
                    chunk_text=payload.get("chunk_text", ""),
                    chunk_type=payload.get("chunk_type", "paragraph"),
                    parser=payload.get("parser", "baseline"),
                    source_parser=payload.get("source_parser"),
                    fallback_reason=payload.get("fallback_reason"),
                    score=float(p.score),
                    source_url=payload.get("source_url"),
                )
            )
        return out

    def delete_document(self, document_id: str) -> None:
        from qdrant_client.http import models as qm

        self.client.delete(
            collection_name=self.s.qdrant_collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))])
            ),
        )

    def count(self) -> int:
        from qdrant_client.http import models as qm

        res = self.client.count(collection_name=self.s.qdrant_collection, exact=True, count_filter=None)
        return int(getattr(res, "count", 0))


def store_available(settings: Settings | None = None) -> bool:
    """Cheap readiness probe used by the API/scripts before heavy calls."""
    s = settings or get_settings()
    try:
        store = QdrantStore(s)
        store.client.get_collections()
        return True
    except Exception as exc:
        log.warning("qdrant not reachable at %s: %s", s.qdrant_url, exc)
        return False


# Silence unused import warnings for Path (kept for future file-based helpers).
_ = Path
