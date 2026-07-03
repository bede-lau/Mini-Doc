"""Shared pytest fixtures.

Tests exercise behaviour through public interfaces (no Qdrant, no embeddings,
no API key). They run fast and offline.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is importable when pytest is invoked from anywhere.
_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest  # noqa: E402

from packages.core.config import Settings  # noqa: E402
from packages.core.schemas.evidence import RetrievalHit  # noqa: E402


@pytest.fixture()
def settings(tmp_path) -> Settings:
    """Settings pinned to a tmp repo root so tests never touch real data dirs."""
    return Settings(
        repo_root=tmp_path,
        abstention_threshold=0.35,
        chunk_size=700,
        chunk_overlap=120,
        top_k=8,
    )


def make_hit(chunk_id, filename, page, text, score, section=None, document_id="d1"):
    return RetrievalHit(
        chunk_id=chunk_id,
        document_id=document_id,
        filename=filename,
        page_start=page,
        page_end=page,
        section=section,
        chunk_text=text,
        score=score,
    )


@pytest.fixture()
def hit():
    return make_hit
