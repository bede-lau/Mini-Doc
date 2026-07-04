"""Reproducible benchmark runner.

Reads the committed benchmark set (questions + expected sources/answers), runs
retrieval + grounded QA for each question, and writes raw outputs, retrieved
chunks, scores, parser scores, summary, run config and environment to
results/<run_id>/. Raw outputs are always saved, and failures are never hidden.
"""
from __future__ import annotations

import csv
import json
import platform
import re
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path

from packages.core.config import Settings, get_settings
from packages.core.evaluation import scoring
from packages.core.registry import DocumentRegistry
from packages.core.utils.logging import get_logger
from packages.core.utils.timeutil import now_iso

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
# CSV helpers
# --------------------------------------------------------------------------- #
def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _index_csv(path: Path, key: str) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {row[key]: row for row in csv.DictReader(fh)}


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    # Merge keys across rows so columns are stable.
    for r in rows[1:]:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _int(v) -> int | None:
    try:
        return int(str(v).strip()) if str(v).strip() else None
    except (ValueError, TypeError):
        return None


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "y")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _unsupported_claims(answer) -> int:
    """Claims whose text does not appear in any retrieved chunk (hallucination proxy)."""
    texts = [_norm(h.chunk_text) for h in answer.retrieved_chunks]
    if not answer.claims:
        return 0
    bad = 0
    for cl in answer.claims:
        probe = _norm(cl.claim_text)[:60]
        if probe and not any(probe in t for t in texts):
            bad += 1
    return bad


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def _aggregate(rows: list[dict]) -> dict:
    keys = ["hit_at_1", "recall_at_3", "recall_at_5", "mrr", "citation_page_match",
            "abstention_correctness"]
    out = {k: scoring.mean([r.get(k) for r in rows]) for k in keys}
    out["questions"] = len(rows)
    out["insufficient_evidence_answers"] = sum(
        1 for r in rows if r.get("answer_type") == "insufficient_evidence"
    )
    out["unsupported_claim_total"] = sum(int(r.get("unsupported_claim_count") or 0) for r in rows)
    return out


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #
def _write_summary(out_dir: Path, rows: list[dict], agg: dict, run_id: str) -> None:
    failures = [
        r for r in rows
        if r.get("hit_at_1") == 0 or r.get("abstention_correctness") == 0
    ]
    lines = [
        f"# Benchmark summary — {run_id}",
        "",
        f"_Generated: {now_iso()}_",
        "",
        "## Aggregate metrics",
        "",
        f"- Questions: **{agg['questions']}**",
        f"- hit_at_1: **{agg['hit_at_1']}**",
        f"- recall_at_3: **{agg['recall_at_3']}**",
        f"- recall_at_5: **{agg['recall_at_5']}**",
        f"- MRR: **{agg['mrr']}**",
        f"- citation_page_match: **{agg['citation_page_match']}**",
        f"- abstention_correctness: **{agg['abstention_correctness']}**",
        f"- insufficient_evidence answers: **{agg['insufficient_evidence_answers']}**",
        f"- unsupported_claim_total (proxy): **{agg['unsupported_claim_total']}**",
        "",
        "## Top failures",
        "",
    ]
    if not failures:
        lines.append("_No retrieval or abstention failures detected._")
    else:
        lines.append("| question_id | hit_at_1 | abstention_correct | expected_document |")
        lines.append("|---|---|---|---|")
        for r in failures[:25]:
            lines.append(
                f"| {r['question_id']} | {r.get('hit_at_1')} | "
                f"{r.get('abstention_correctness')} | {r.get('expected_document','')} |"
            )
    lines += [
        "",
        "## Manual scoring (to be filled)",
        "",
        "Fill `manual_answer_correctness`, `manual_citation_support`, "
        "`manual_table_score`, `manual_reading_order_score` in scores.csv.",
        "",
        "_Manual metrics are committed by a human after inspecting raw outputs; "
        "they are never auto-filled._",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_parser_scores(out_dir: Path, settings: Settings) -> None:
    reg = DocumentRegistry(settings=settings)
    metrics_path = settings.parsed_dir / "_parse_metrics.jsonl"
    per_doc: list[dict] = []
    if metrics_path.exists():
        for line in metrics_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    per_doc.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    rows = []
    if per_doc:
        for parser in sorted({d.get("parser") for d in per_doc}):
            docs = [d for d in per_doc if d.get("parser") == parser]
            pages = sum(int(d.get("page_count", 0)) for d in docs)
            empty = sum(int(d.get("empty_pages", 0)) for d in docs)
            elapsed = sum(float(d.get("elapsed_seconds", 0)) for d in docs)
            crashes = sum(1 for d in docs if d.get("crashed"))
            rows.append({
                "parser": parser,
                "document_count": len(docs),
                "parse_success_rate": round((len(docs) - crashes) / len(docs), 4) if docs else 0,
                "empty_page_rate": round(empty / pages, 4) if pages else 0,
                "avg_latency_seconds_per_page": round(elapsed / pages, 4) if pages else 0,
                "crash_count": crashes,
                "manual_table_score": "",
                "manual_reading_order_score": "",
            })
    else:
        st = reg.parser_stats()
        rows.append({
            "parser": "unknown",
            "document_count": st["document_count"],
            "parse_success_rate": st["parse_success_rate"],
            "empty_page_rate": "",
            "avg_latency_seconds_per_page": "",
            "crash_count": st["crash_count"],
            "manual_table_score": "",
            "manual_reading_order_score": "",
        })
    _write_csv(out_dir / "parser_scores.csv", rows)


def _write_run_config(out_dir: Path, settings: Settings) -> None:
    cfg = (
        f"# Run config for benchmark at {now_iso()}\n"
        f"llm_provider: {settings.effective_llm_provider}\n"
        f"llm_model: {settings.llm_model}\n"
        f"llm_temperature: {settings.llm_temperature}\n"
        f"embedding_model: {settings.embedding_model}\n"
        f"embedding_dim: {settings.embedding_dim}\n"
        f"chunk_size: {settings.chunk_size}\n"
        f"chunk_overlap: {settings.chunk_overlap}\n"
        f"top_k: {settings.top_k}\n"
        f"abstention_threshold: {settings.abstention_threshold}\n"
        f"qdrant_collection: {settings.qdrant_collection}\n"
    )
    (out_dir / "run_config.yaml").write_text(cfg, encoding="utf-8")


def _write_environment(out_dir: Path, settings: Settings) -> None:
    pkgs = ["fastapi", "uvicorn", "qdrant-client", "sentence-transformers", "docling",
            "pdfplumber", "pymupdf", "pydantic", "httpx", "tiktoken"]
    versions = []
    for p in pkgs:
        try:
            versions.append(f"{p}=={metadata.version(p)}")
        except metadata.PackageNotFoundError:
            versions.append(f"{p}=NOT INSTALLED")
    env = (
        f"python: {sys.version.split()[0]}\n"
        f"platform: {platform.platform()}\n"
        f"generated_at: {now_iso()}\n"
        f"llm_provider_effective: {settings.effective_llm_provider}\n"
        f"llm_model: {settings.llm_model}\n"
        "\npackages:\n" + "\n".join(versions) + "\n"
    )
    (out_dir / "environment.txt").write_text(env, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def run_benchmark(
    run_id: str = "run_001",
    retriever=None,
    settings: Settings | None = None,
) -> dict:
    s = settings or get_settings()
    out_dir = s.results_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    questions_path = s.benchmark_dir / "questions.csv"
    if not questions_path.exists():
        raise FileNotFoundError(
            f"benchmark questions not found at {questions_path}. "
            "Commit the benchmark set before running."
        )

    questions = _read_csv(questions_path)
    expected_sources = _index_csv(s.benchmark_dir / "expected_sources.csv", "question_id")
    expected_answers = _index_csv(s.benchmark_dir / "expected_answers.csv", "question_id")

    if retriever is None:
        from packages.core.retrieval.retriever import Retriever

        retriever = Retriever(settings=s)

    from packages.core.generation.qa import qa

    rows: list[dict] = []
    raw_lines: list[str] = []
    chunk_lines: list[str] = []

    for q in questions:
        qid = q.get("question_id", "")
        question = q.get("question", "").strip()
        gt = expected_sources.get(qid, {})
        exp_doc = (gt.get("expected_document") or q.get("expected_document") or "").strip()
        ps = _int(gt.get("expected_page_start") or q.get("expected_page_start"))
        pe = _int(gt.get("expected_page_end") or q.get("expected_page_end"))
        should_abstain = _bool(q.get("should_abstain"))

        hits = retriever.retrieve(question, top_k=s.top_k)
        ans = qa(question, retriever, settings=s)

        rows.append({
            "question_id": qid,
            "domain": q.get("domain", ""),
            "task_type": q.get("task_type", ""),
            "expected_document": exp_doc,
            "hit_at_1": scoring.hit_at_1(hits, exp_doc),
            "recall_at_3": scoring.recall_at_k(hits, exp_doc, 3),
            "recall_at_5": scoring.recall_at_k(hits, exp_doc, 5),
            "mrr": scoring.mrr(hits, exp_doc),
            "citation_page_match": scoring.citation_page_match(ans.citations, exp_doc, ps, pe),
            "answer_type": ans.answer_type,
            "should_abstain": should_abstain,
            "abstention_correctness": scoring.abstention_correctness(ans.answer_type, should_abstain),
            "unsupported_claim_count": _unsupported_claims(ans),
            "manual_answer_correctness": "",
            "manual_citation_support": "",
        })
        raw_lines.append(json.dumps({
            "question_id": qid,
            "question": question,
            "answer_type": ans.answer_type,
            "answer": ans.answer,
            "claims": [c.model_dump() for c in ans.claims],
            "citations": [c.model_dump() for c in ans.citations],
            "expected_answer_short": expected_answers.get(qid, {}).get("expected_answer_short", ""),
        }))
        chunk_lines.append(json.dumps({
            "question_id": qid,
            "chunks": [h.model_dump() for h in hits],
        }))

    _write_csv(out_dir / "scores.csv", rows)
    (out_dir / "raw_outputs.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (out_dir / "retrieved_chunks.jsonl").write_text("\n".join(chunk_lines) + "\n", encoding="utf-8")
    agg = _aggregate(rows)
    _write_summary(out_dir, rows, agg, run_id)
    _write_parser_scores(out_dir, s)
    _write_run_config(out_dir, s)
    _write_environment(out_dir, s)

    log.info("benchmark %s complete: %d questions -> %s", run_id, len(rows), out_dir)
    return {"run_id": run_id, "questions": len(rows), "output_dir": str(out_dir), "summary": agg}


def list_runs(settings: Settings | None = None) -> list[dict]:
    s = settings or get_settings()
    runs = []
    if s.results_dir.exists():
        for d in sorted(s.results_dir.iterdir()):
            summary = d / "summary.md"
            if d.is_dir() and summary.exists():
                runs.append({"run_id": d.name, "path": str(d), "has_summary": True})
    return runs


def load_run_result(run_id: str, settings: Settings | None = None) -> dict:
    """Load aggregate metrics for a completed benchmark run."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id or ""):
        raise ValueError("invalid run_id")
    s = settings or get_settings()
    out_dir = s.results_dir / run_id
    scores = out_dir / "scores.csv"
    if not scores.exists():
        raise FileNotFoundError(f"benchmark scores not found for {run_id}")
    rows = _read_csv(scores)
    agg = _aggregate(rows)
    return {"run_id": run_id, "questions": len(rows), "output_dir": str(out_dir), "summary": agg}


def delete_run(run_id: str, settings: Settings | None = None) -> dict:
    """Delete a benchmark run directory and everything under it.

    Refuses anything that isn't a single path segment under ``results_dir`` so
    a crafted run_id can't escape the results root.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id or ""):
        raise ValueError("invalid run_id")
    s = settings or get_settings()
    out_dir = (s.results_dir / run_id).resolve()
    if not out_dir.is_relative_to(s.results_dir.resolve()):
        raise ValueError("run_id escapes results_dir")
    if not out_dir.exists():
        raise FileNotFoundError(f"benchmark run not found: {run_id}")
    if not out_dir.is_dir():
        raise ValueError(f"not a run directory: {run_id}")

    import shutil

    removed_files = [str(p) for p in out_dir.rglob("*") if p.is_file()]
    shutil.rmtree(out_dir)
    log.info("deleted benchmark run %s (%d files)", run_id, len(removed_files))
    return {"run_id": run_id, "deleted": True, "removed_files": removed_files}


# datetime import retained for potential timestamps; now_iso is the primary path.
_ = datetime
