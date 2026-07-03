"""Download the public PDFs listed in manifests/public_docs.csv.

Usage:
    python scripts/download_public_docs.py [--only <filename>] [--force]

Writes PDFs to data/raw_docs/. Verifies the %PDF magic bytes; rows whose URL is
not a direct PDF (e.g. the ACRA landing page) are flagged in
data/raw_docs/_download_report.csv and must be fetched manually — see
MANUAL_TASKS.md.
"""
from __future__ import annotations

import argparse
import csv
import re

from common import REPO_ROOT, bootstrap, ensure_data_dirs, read_manifest

bootstrap()
from packages.core.config import get_settings  # noqa: E402
from packages.core.utils.logging import get_logger  # noqa: E402

log = get_logger("download")
PDF_MAGIC = b"%PDF"
# Strict allow-list: bare PDF filename, no path separators or traversal.
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.pdf$", re.IGNORECASE)
_DOWNLOAD_HEADERS = {
    # Some official sites return an HTML interstitial unless the request looks
    # like a browser. Keep this deterministic and minimal; PDF magic-byte
    # validation below still rejects non-PDF responses.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
}


def _save_pdf(url: str, dest, httpx):
    """Stream a download to dest.part, returning the first 4 bytes (magic)."""
    part = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream(
        "GET",
        url,
        follow_redirects=True,
        timeout=120,
        headers=_DOWNLOAD_HEADERS,
    ) as resp:
        resp.raise_for_status()
        first = bytearray()
        with part.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=1 << 16):
                if len(first) < 4:
                    first.extend(chunk[: 4 - len(first)])
                fh.write(chunk)
        return bytes(first), part


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="download only this filename")
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    args = ap.parse_args()

    import httpx

    s = get_settings()
    ensure_data_dirs(s)
    rows = [r for r in read_manifest() if not args.only or r["filename"] == args.only]
    report_path = s.raw_docs_dir / "_download_report.csv"
    report_rows: list[dict] = []

    successes = 0
    for row in rows:
        filename = row["filename"]
        url = row["source_url"]
        entry = {"filename": filename, "url": url, "status": "", "note": ""}
        if not _NAME_RE.match(filename):
            entry["status"] = "invalid_filename"
            entry["note"] = "filename failed the strict allow-list; refusing to write."
            report_rows.append(entry)
            log.warning("INVALID FILENAME: %r", filename)
            continue
        dest = s.raw_docs_dir / filename
        if not dest.resolve().is_relative_to(s.raw_docs_dir.resolve()):
            entry["status"] = "invalid_filename"
            entry["note"] = "resolved path escapes raw_docs."
            report_rows.append(entry)
            continue
        if dest.exists() and not args.force:
            entry["status"] = "skipped_exists"
            report_rows.append(entry)
            log.info("skip (exists): %s", filename)
            continue
        try:
            magic, part = _save_pdf(url, dest, httpx)
            if magic[:4] != PDF_MAGIC:
                part.unlink(missing_ok=True)
                entry["status"] = "not_pdf"
                entry["note"] = "URL did not return a PDF (likely a landing page). Download manually."
                log.warning("NOT PDF: %s <- %s", filename, url)
            else:
                part.replace(dest)
                entry["status"] = "ok"
                successes += 1
                log.info("ok: %s", filename)
        except Exception as exc:
            entry["status"] = "error"
            entry["note"] = str(exc)[:200]
            log.error("error downloading %s: %s", filename, exc)
        report_rows.append(entry)

    with report_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["filename", "url", "status", "note"])
        w.writeheader()
        w.writerows(report_rows)

    log.info("downloaded %d/%d PDFs. report: %s", successes, len(rows), report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
