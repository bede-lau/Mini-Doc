"""Process-wide singletons for the FastAPI app.

Registry is cheap and always available. The retriever is expensive (loads the
embedding model and needs Qdrant), so it is cached but built lazily — endpoints
that need it call get_retriever_or_503().
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from packages.core.config import get_settings
from packages.core.registry import DocumentRegistry


@lru_cache(maxsize=1)
def get_registry() -> DocumentRegistry:
    return DocumentRegistry()


@lru_cache(maxsize=1)
def _retriever():
    from packages.core.retrieval.retriever import Retriever

    return Retriever()


def get_retriever_or_503():
    try:
        return _retriever()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Retrieval backend unavailable: {exc}. "
                "Start Qdrant (`docker compose up -d qdrant`) and index documents "
        "(`python scripts/index_docs.py --parser hybrid`)."
            ),
        ) from exc


def reset_singletons() -> None:
    """Test hook: drop cached registry/retriever."""
    get_registry.cache_clear()
    _retriever.cache_clear()
