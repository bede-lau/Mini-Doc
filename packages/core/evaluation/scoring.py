"""Deterministic retrieval/answer/citation metrics.

All functions are pure and accept either schema objects (RetrievalHit /
Citation) or plain dicts, so the same math works in the benchmark runner and in
unit tests. No LLM calls live here — manual and LLM-as-judge scores are scored
separately and left for human/optional-judge fill.
"""
from __future__ import annotations

from typing import Any


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _filename(obj: Any) -> str:
    return str(_get(obj, "filename", "") or "")


def hit_at_1(hits: list, expected_document: str | None) -> int:
    if not expected_document or not hits:
        return 0
    return 1 if _filename(hits[0]) == expected_document else 0


def recall_at_k(hits: list, expected_document: str | None, k: int) -> int:
    if not expected_document or not hits:
        return 0
    return 1 if any(_filename(h) == expected_document for h in hits[:k]) else 0


def mrr(hits: list, expected_document: str | None) -> float:
    if not expected_document:
        return 0.0
    for i, h in enumerate(hits, start=1):
        if _filename(h) == expected_document:
            return round(1.0 / i, 4)
    return 0.0


def citation_page_match(
    citations: list,
    expected_document: str | None,
    expected_page_start: int | None,
    expected_page_end: int | None,
) -> int:
    """1 if any citation points at the expected doc (and page band, if given)."""
    if not expected_document or not citations:
        return 0
    matching = [c for c in citations if _filename(c) == expected_document]
    if not matching:
        return 0
    if expected_page_start is not None and expected_page_end is not None:
        in_band = any(
            expected_page_start <= int(_get(c, "page", 0) or 0) <= expected_page_end for c in matching
        )
        return 1 if in_band else 0
    return 1


def abstention_correctness(answer_type: str, should_abstain: bool) -> int:
    """1 iff the abstention decision matches the labelled expectation."""
    actually_abstained = answer_type == "insufficient_evidence"
    return 1 if actually_abstained == bool(should_abstain) else 0


def mean(values: list) -> float:
    nums = [float(v) for v in values if v is not None]
    return round(sum(nums) / len(nums), 4) if nums else 0.0
