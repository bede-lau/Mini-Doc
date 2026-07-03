"""Central configuration for EvidenceOS Mini.

All values are environment-driven with sensible defaults, so the application
runs out of the box with no API key (offline answer mode) and a local Qdrant.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_repo_root() -> Path:
    # packages/core/config.py -> repo root is two parents up (core -> packages -> root).
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Paths / locale ---
    repo_root: Path = Path(_default_repo_root())
    timezone: str = "Asia/Singapore"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "evidenceos_chunks"

    # --- Embeddings ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    model_cache_dir: str | None = None

    # --- Chunking ---
    chunk_size: int = 700
    chunk_overlap: int = 120

    # --- Retrieval ---
    top_k: int = 8
    abstention_threshold: float = 0.35

    # --- LLM ---
    llm_provider: Literal["offline", "openai", "anthropic"] = "offline"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_temperature: float = 0.0
    force_offline: bool = False

    # ------------------------------------------------------------------ #
    # Derived paths
    # ------------------------------------------------------------------ #
    @property
    def data_dir(self) -> Path:
        return self.repo_root / "data"

    @property
    def raw_docs_dir(self) -> Path:
        return self.data_dir / "raw_docs"

    @property
    def parsed_dir(self) -> Path:
        return self.data_dir / "parsed"

    @property
    def chunks_dir(self) -> Path:
        return self.data_dir / "chunks"

    @property
    def results_dir(self) -> Path:
        return self.repo_root / "results"

    @property
    def manifest_path(self) -> Path:
        return self.repo_root / "manifests" / "public_docs.csv"

    @property
    def benchmark_dir(self) -> Path:
        return self.repo_root / "benchmark"

    @property
    def registry_path(self) -> Path:
        return self.data_dir / "registry.json"

    @property
    def hf_cache_dir(self) -> Path | None:
        return Path(self.model_cache_dir) if self.model_cache_dir else None

    @property
    def effective_llm_provider(self) -> str:
        """Resolve the provider actually used.

        Offline is forced when no key is configured for a paid provider, or when
        force_offline is set. This keeps the benchmark reproducible and the app
        runnable without credentials.
        """
        if self.force_offline:
            return "offline"
        if self.llm_provider == "offline":
            return "offline"
        if self.llm_provider in ("openai", "anthropic") and not self.llm_api_key:
            return "offline"
        return self.llm_provider


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
