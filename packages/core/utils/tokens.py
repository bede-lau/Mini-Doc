"""Token estimation.

Chunk sizes are specified in tokens (~500-900). We use tiktoken when available
for accuracy and fall back to a deterministic heuristic otherwise, so the
pipeline never hard-fails on a missing optional dependency.
"""
from __future__ import annotations

try:  # optional dependency
    import tiktoken  # type: ignore

    _ENC = tiktoken.get_encoding("cl100k_base")

    def _count_tiktoken(text: str) -> int:
        return len(_ENC.encode(text))
except Exception:  # pragma: no cover - tiktoken absent in lean installs
    _ENC = None

    def _count_tiktoken(text: str) -> int:  # type: ignore[misc]
        raise RuntimeError("tiktoken unavailable")


def estimate_tokens(text: str) -> int:
    """Approximate token count. At least 1 for non-empty text."""
    if not text:
        return 0
    if _ENC is not None:
        try:
            return _count_tiktoken(text)
        except Exception:
            pass
    # Heuristic: ~4 characters per token (GPT-family average) bounded by word
    # count. Deterministic and dependency-free.
    words = len(text.split())
    chars = len(text)
    return max(1, max(words, chars // 4))
