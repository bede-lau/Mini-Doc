"""Shared helpers for CLI scripts (path bootstrap, manifest, data dirs)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def bootstrap() -> None:
    """Ensure the repo root is importable when a script is run directly."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def read_manifest() -> list[dict]:
    from packages.core.config import get_settings

    path = get_settings().manifest_path
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def manifest_index() -> dict[str, dict]:
    return {row["filename"]: row for row in read_manifest()}


def ensure_data_dirs(settings=None) -> None:
    from packages.core.config import get_settings

    s = settings or get_settings()
    for d in (s.raw_docs_dir, s.parsed_dir, s.chunks_dir, s.results_dir):
        d.mkdir(parents=True, exist_ok=True)
