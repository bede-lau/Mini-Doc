"""Document deletion removes registry entries and local artifacts."""
from __future__ import annotations

from packages.core.registry import DocumentRegistry
from packages.core.schemas.document import DocumentMeta
from services.api.routes import documents as document_routes


class _FakeQdrantStore:
    deleted: list[str] = []

    def __init__(self, settings):
        self.settings = settings

    def delete_document(self, document_id: str) -> None:
        self.deleted.append(document_id)


def test_delete_document_removes_registry_files_and_metrics(settings, monkeypatch):
    registry = DocumentRegistry(settings=settings)
    doc = DocumentMeta(
        document_id="doc123",
        filename="delete-me.pdf",
        domain="demo",
        document_type="policy",
        parser="docling",
        parse_status="success",
    )
    registry.upsert(doc)

    raw = settings.raw_docs_dir / doc.filename
    parsed = settings.parsed_dir / "docling" / f"{doc.document_id}_parsed.json"
    chunks = settings.chunks_dir / "docling" / f"{doc.document_id}.jsonl"
    metrics = settings.parsed_dir / "_parse_metrics.jsonl"
    for path in (raw, parsed, chunks, metrics):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"%PDF-1.4")
    parsed.write_text("{}", encoding="utf-8")
    chunks.write_text("{}", encoding="utf-8")
    metrics.write_text(
        '{"document_id":"doc123","parser":"docling"}\n'
        '{"document_id":"keep","parser":"docling"}\n',
        encoding="utf-8",
    )

    _FakeQdrantStore.deleted.clear()
    monkeypatch.setattr(document_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(document_routes, "get_registry", lambda: registry)
    monkeypatch.setattr("packages.core.retrieval.qdrant_store.QdrantStore", _FakeQdrantStore)

    response = document_routes.delete_document(doc.document_id)

    assert response.deleted is True
    assert registry.get(doc.document_id) is None
    assert not raw.exists()
    assert not parsed.exists()
    assert not chunks.exists()
    assert "doc123" not in metrics.read_text(encoding="utf-8")
    assert "keep" in metrics.read_text(encoding="utf-8")
    assert _FakeQdrantStore.deleted == [doc.document_id]
