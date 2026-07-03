"""Qdrant client compatibility behavior."""

from types import SimpleNamespace

from packages.core.config import Settings
from packages.core.retrieval.qdrant_store import QdrantStore


class QueryOnlyClient:
    def query_points(self, **kwargs):
        self.kwargs = kwargs
        point = SimpleNamespace(
            id="p1",
            score=0.8,
            payload={
                "chunk_id": "c1",
                "document_id": "d1",
                "filename": "doc.pdf",
                "page_start": 2,
                "page_end": 2,
                "chunk_text": "evidence",
                "chunk_type": "paragraph",
                "parser": "docling",
            },
        )
        return SimpleNamespace(points=[point])


def test_search_supports_query_points_client_api():
    store = QdrantStore(Settings())
    client = QueryOnlyClient()
    store._client = client

    hits = store.search([0.1, 0.2], top_k=1)

    assert client.kwargs["query"] == [0.1, 0.2]
    assert hits[0].chunk_id == "c1"
    assert hits[0].filename == "doc.pdf"
    assert hits[0].score == 0.8

