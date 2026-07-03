"""Retrieval orchestration: embed query -> search Qdrant -> RetrievalHits."""
from __future__ import annotations

from packages.core.config import Settings, get_settings
from packages.core.retrieval.embeddings import Embedder
from packages.core.retrieval.qdrant_store import QdrantStore
from packages.core.schemas.evidence import RetrievalHit


class Retriever:
    def __init__(
        self,
        embedder: Embedder | None = None,
        store: QdrantStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.s = settings or get_settings()
        self.embedder = embedder or Embedder(self.s)
        self.store = store or QdrantStore(self.s)
        self.store.ensure_collection()

    def retrieve(self, query: str, top_k: int | None = None, filters: dict | None = None) -> list[RetrievalHit]:
        vec = self.embedder.encode_one(query)
        return self.store.search(vec, top_k or self.s.top_k, filters)
