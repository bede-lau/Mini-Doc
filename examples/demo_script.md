# Demo Script — 5-minute walkthrough

Audience: Marcus/Brian (Akro). Goal: show the regulated-analyst loop end to end —
ingest → structure → ground → reason → report → benchmark — and the two-commit
benchmark-integrity proof.

**Setup (before recording):** Qdrant up; docs downloaded/parsed/indexed (docling);
backend + frontend running. Open four tabs: README, app Library, Q&A, Benchmark.

## 0:00 — Framing (README)

> "This is EvidenceOS Mini, a document-intelligence work trial for Akro. It turns
> public regulated documents into structured, citable knowledge, answers with
> exact source provenance, abstains honestly, generates an audit-ready report, and
> ships with a reproducible benchmark committed before its results."

Point at the architecture diagram and the structural-grounding note
(`Claim`/`Answer` reject unsupported answers).

## 0:40 — Document Library

- Show the 9-document bundle with domain, parser, page count, status, SHA256.
- Note both parsers ran; the **baseline vs Docling** contrast is the engineering
  signal (tables, reading order).

## 1:20 — Evidence Q&A (grounded)

Ask: **"Who qualifies as a registrable controller?"**

- Show the answer with **citation cards** (filename + page + section).
- Toggle **retrieved chunks** to show the raw evidence and scores.

## 2:20 — Evidence Q&A (abstention)

Ask something out of scope: **"What are the GDPR lawful bases for processing?"**

- Show the clear **"Insufficient evidence in the reviewed documents."** state —
  no hallucination, no fabricated citation.

## 2:50 — Report Builder

- Pick **General Compliance Intelligence Review** → Generate.
- Scroll to the **Evidence Table** (mandatory) and **Missing Information** section.
- Note every finding traces back to a cited chunk.

## 3:50 — Benchmark Dashboard

- Run `run_001` (or show the committed result).
- Point at the metric tiles: hit@1, recall@5, MRR, citation-page match,
  abstention correctness, unsupported-claim proxy.
- Open `results/run_001/summary.md` and `raw_outputs.jsonl` to show raw outputs
  and failures are kept.

## 4:30 — Benchmark integrity (git)

- `git log --oneline` — show the ordering:
  1. `test: add fixed benchmark set and scoring script`
  2. `eval: add first reproducible benchmark run`
- "Questions were committed before results. Anyone can rerun locally with
  `python scripts/run_benchmark.py --run-id run_001`."

## 4:55 — Close

> "Small, honest, reliable. Built to show engineering judgement — grounding is
> enforced by the data model, abstention is first-class, and the benchmark is
> reproducible without an API key. Here's what I'd harden next at Akro."
- One line on the improvement list (hybrid retrieval, bbox provenance in UI).
