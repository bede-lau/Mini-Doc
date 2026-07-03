"""Local embeddings via SentenceTransformers.

Model loads lazily and is cached per process. The default model
(BAAI/bge-small-en-v1.5, 384-dim) downloads on first use; see MANUAL_TASKS for
the offline/offline-machine note.
"""
from __future__ import annotations

from packages.core.config import Settings, get_settings
from packages.core.utils.logging import get_logger

log = get_logger(__name__)


class Embedder:
    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            cache = str(self.s.hf_cache_dir) if self.s.hf_cache_dir else None
            log.info("loading embedding model %s (cache=%s)", self.s.embedding_model, cache)
            self._model = SentenceTransformer(self.s.embedding_model, cache_folder=cache)
        return self._model

    @property
    def dim(self) -> int:
        return self.s.embedding_dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, v)) for v in vecs]

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0]
