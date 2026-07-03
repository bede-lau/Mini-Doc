# EvidenceOS Mini

**Audit-ready document intelligence for regulated workflows.** A small, honest,
local-first document-intelligence pipeline built as a technical work sample for
Akro AI: ingest messy regulated PDFs, parse them (baseline + Docling), index with
provenance, answer questions with **exact citations**, **abstain when evidence is
weak**, generate a **compliance-ready report**, and prove it all with a
**reproducible benchmark** whose questions were committed before the results.

This is deliberately *not* a "chat-with-PDF" wrapper.

---

## 1. What this is

A local web app (FastAPI backend + Next.js frontend, Qdrant vector DB) that:

1. ingests public/synthetic regulated PDFs;
2. parses them with a **baseline** parser (pdfplumber) and a **Docling** parser;
3. chunks and indexes text/tables with rich metadata;
4. answers questions with RAG and **exact citations (filename + page)**;
5. **abstains** ("Insufficient evidence…") when retrieval is weak;
6. generates a professional **compliance-ready Markdown report**;
7. runs a **reproducible benchmark** committed before its results.

The pipeline runs **with no API key**: a deterministic offline grounding mode is
the default, so the benchmark is reproducible on any machine. An optional LLM
adapter (OpenAI-compatible or Anthropic) can be enabled via env.

## 2. Why this maps to Akro

Akro positions itself as operational data intelligence for regulated industries —
on-premise/sovereign AI workspaces that turn documents, records, and institutional
knowledge into automated workflows with **precision, privacy, explainability,
source provenance, and agentic knowledge layers**. Their finance/insurance/defence
case studies emphasise: ingest heterogeneous documents, preserve structure
(tables, layout), **ground every extracted fact to an exact source**, answer with
citations, and produce defensible reports.

This demo exercises that exact loop — **ingest → structure → ground → reason →
report → benchmark** — with page/section provenance, mandatory citation trails,
abstention, and an audit-ready report template.

See `AKRO_BUILD_REFERENCE.md` for the full alignment rationale and sources.

## 3. Demo video

> _Placeholder:_ `[Loom / MP4 link]` — 5-minute walkthrough following
> `examples/demo_script.md`.

## 4. Architecture

```text
apps/web (Next.js + TS)            services/api (FastAPI)
  Library  ──┐                       /ingest  /documents  /parse  /index
  Q&A      ──┼── HTTP (JSON) ───────▶ /search  /qa
  Reports  ──┤                       /reports/generate
  Benchmark ─┘                       /benchmarks/run  /benchmarks/results
                                       │
                            packages/core (importable as packages.core)
   ┌───────────────────────────────────┴──────────────────────────────────┐
   │ parsers/   baseline (pdfplumber) · docling · ocr(optional)           │
   │ chunking/  token-aware, page/section-preserving, table-aware         │
   │ retrieval/ SentenceTransformers embeddings · Qdrant store · retriever│
   │ generation/ LLM adapter (openai|anthropic|offline) · grounded QA     │
   │ reporting/ builder + Markdown renderer (audit template)              │
   │ evaluation/ deterministic scoring + reproducible benchmark runner    │
   │ schemas/   Pydantic source-of-truth (Document, Chunk, Answer, ...)   │
   │ registry/  JSON document registry · pipeline orchestration           │
   └──────────────────────────────────────────────────────────────────────┘
                            │
             Qdrant (Docker)  ◀── vectors + payload metadata

data/   raw_docs · parsed · chunks      results/   run_001/* (committed)
benchmark/  questions + expected_* (committed BEFORE results)
```

**Grounding is structural, not aspirational:** `Claim` and `Answer` are Pydantic
models that *reject* unsupported answers at construction time. A "supported"
answer physically cannot be built without a citation that exists in the retrieved
chunks.

## 5. Quickstart

Requirements: **Python 3.11 or 3.12** (Docling/torch wheels are not yet on 3.13+),
Docker, Node 18+.

```bash
cp .env.example .env
docker compose up -d qdrant
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -r services/api/requirements.txt
pip install -e .            # makes packages.core / services importable
```

## 6. Download the public docs

```bash
python scripts/download_public_docs.py
```

Downloads the 9 public PDFs into `data/raw_docs/`. **Note:** the ACRA document is
a landing page, not a direct PDF — fetch "Guidance on Register of Controllers for
Companies" v2 (16 Jun 2025) manually and place it as
`data/raw_docs/acra-registrable-controllers-guidance-2025.pdf`. See
`MANUAL_TASKS.md`.

## 7. Parse and index

```bash
python scripts/parse_docs.py --parser baseline   # fast baseline
python scripts/parse_docs.py --parser docling     # structured (tables, layout)
python scripts/index_docs.py --parser docling     # embed + upsert into Qdrant
```

The first Docling run may download layout/OCR models (~hundreds of MB); the first
index run downloads the `bge-small` embedding model (~130 MB). Both cache locally.

## 8. Run the app

Backend:

```bash
uvicorn services.api.main:app --reload
# API at http://localhost:8000  ·  docs at /docs
```

Frontend (separate shell):

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

## 9. Generate a report

From the UI (**Report Builder**) or:

```bash
curl -X POST http://localhost:8000/reports/generate \
  -H 'Content-Type: application/json' \
  -d '{"report_type":"general_compliance_intelligence"}'
```

Reports are written to `results/reports/`. A hand-authored sample lives at
`examples/sample_compliance_report.md`.

## 10. Run the benchmark

```bash
python scripts/run_benchmark.py --run-id run_001
cat results/run_001/summary.md
```

The benchmark works **offline** (no API key), so the run is deterministic and
reproducible.

## 11. Benchmark integrity

> **Benchmark integrity:** the benchmark questions, expected answers, expected
> sources, and scoring script were committed **before** running the test. Results
> were committed separately. Raw retrieved chunks and raw model outputs are
> included so the run can be inspected or rerun locally.

Enforced by a two-commit rule (see `benchmark/README.md`):

- **Commit 1** — the fixed set + scoring script (`test: add fixed benchmark set`).
- **Commit 2** — the results only (`eval: add first reproducible benchmark run`).

Questions are never edited after results are seen; changes go into a new
`benchmark_v2/` → `results/run_002/`.

## 12. Result summary

> _Fill after running_: `results/run_001/summary.md` reports `hit_at_1`,
> `recall_at_3/5`, `MRR`, `citation_page_match`, `abstention_correctness`, and the
> unsupported-claim proxy. Because the default answer mode is deterministic
> extractive grounding, scores are stable across machines and runs.

## 13. Failure analysis

Failures are surfaced, not hidden:

- `results/run_001/raw_outputs.jsonl` — every answer, including abstentions.
- `results/run_001/retrieved_chunks.jsonl` — what was retrieved per question.
- `results/run_001/scores.csv` — per-question metrics + blank **manual** columns.
- `summary.md` lists top retrieval/abstention failures.

Known failure modes to expect (honest design limits): dense-only retrieval (no
BM25 rerank) can miss keyword-specific queries; the offline extractor can only
cite sentences that share terms with the question; the baseline parser loses
reading order and some tables (that contrast is the point of having both parsers).

## 14. Limitations

- Dense embeddings only (no hybrid/BM25 rerank yet — scaffolded in config).
- Page numbers in `expected_sources.csv` are intentionally blank; they are filled
  after parsing (manual or via a future auto-fill step).
- Manual metrics (`manual_answer_correctness`, `manual_citation_support`,
  `manual_table_score`, `manual_reading_order_score`) are left blank for a human
  to fill — they are never auto-generated.
- Docling's API changes between versions; the adapter is defensive but should be
  re-validated against your installed Docling version.
- No auth, no multi-tenancy, no production deployment — by design.

## 15. What I would improve during an Akro internship

- **Hybrid retrieval**: add BM25 + dense fusion and a cross-encoder reranker
  (the config + filter plumbing already exist).
- **Bounding-box provenance to the UI**: surface `bbox` on citations and render
  the highlighted source region (Docling already provides it).
- **A real LLM-judge lane**: wire Ragas/DeepEval behind the existing optional
  metrics, keeping deterministic metrics as the always-on baseline.
- **Page-band auto-fill**: post-parse, map each expected evidence snippet to its
  page so `citation_page_match` is computed automatically.
- **Cross-document entity linking** for KYC (controller ↔ company ↔ filings),
  which is where Akro's "agentic knowledge layer" adds the most value.
- **Table-structure scoring** automated against a DocLayNet sample.

---

## Repo layout

```text
packages/core/   parsers · chunking · retrieval · generation · reporting · evaluation · schemas · registry · pipeline
services/api/    FastAPI app + routes (documents · qa · reports · benchmarks)
apps/web/        Next.js (Library · Q&A · Reports · Benchmark)
scripts/         download_public_docs · parse_docs · index_docs · run_benchmark
manifests/       public_docs.csv
benchmark/       questions · expected_answers · expected_sources · scoring_config · README
data/            raw_docs · parsed · chunks (gitignored, regenerable)
results/         run_001/* (committed) · reports/
examples/        sample_compliance_report · demo_script · technical_memo
tests/           behaviour suite (pytest)
```

## License

MIT. Public demo data only — not legal, financial, insurance, or regulatory advice.
