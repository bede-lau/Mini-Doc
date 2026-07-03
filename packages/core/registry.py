"""Lightweight JSON-backed document registry.

Persists DocumentMeta across runs so /documents, the report inventory, and the
parser metrics work without a dedicated database. File: data/registry.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from packages.core.config import Settings, get_settings
from packages.core.schemas.document import DocumentMeta
from packages.core.utils.logging import get_logger

log = get_logger(__name__)


class DocumentRegistry:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self.path = Path(path) if path else self.s.registry_path
        self.docs: dict[str, DocumentMeta] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.docs = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.docs = {item["document_id"]: DocumentMeta(**item) for item in raw}
        except Exception as exc:
            log.warning("registry load failed (%s); starting empty", exc)
            self.docs = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([d.model_dump() for d in self.docs.values()], indent=2),
            encoding="utf-8",
        )

    def upsert(self, meta: DocumentMeta) -> DocumentMeta:
        self.docs[meta.document_id] = meta
        self.save()
        return meta

    def get(self, document_id: str) -> DocumentMeta | None:
        return self.docs.get(document_id)

    def by_filename(self, filename: str) -> DocumentMeta | None:
        return next((d for d in self.docs.values() if d.filename == filename), None)

    def list(self) -> list[DocumentMeta]:
        return list(self.docs.values())

    def parser_stats(self, parser: str | None = None) -> dict:
        """Aggregate parse metrics used by the benchmark parser section."""
        # Exclude never-parsed docs (parser == "none") unless a specific parser is asked for.
        docs = [
            d for d in self.docs.values()
            if (parser is None and d.parser != "none") or d.parser == parser
        ]
        total = len(docs)
        if not total:
            return {"document_count": 0, "parse_success_rate": 0.0, "crash_count": 0}
        successes = sum(1 for d in docs if d.parse_status == "success")
        partials = sum(1 for d in docs if d.parse_status == "partial")
        crashes = sum(1 for d in docs if d.parse_status == "failed")
        return {
            "document_count": total,
            "parse_success_rate": round((successes + partials) / total, 4),
            "crash_count": crashes,
        }
