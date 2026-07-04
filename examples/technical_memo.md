# Technical Memo ? Mini-Doc

A short, honest account of what worked, what failed, and what I would improve.
Written from the build, not from aspiration.

## What worked

- **Structural grounding.** The single highest-leverage decision was making
  grounding a property of the data model, not a prompt instruction. `Claim` and
  `Answer` are Pydantic models that reject unsupported answers at construction
  time; a "supported" answer cannot be assembled without a citation that exists in
  the retrieved chunks. This makes hallucination a type error, not a hope.
- **Keyless reproducibility.** A deterministic offline-extractive answerer is the
  default, so the benchmark runs identically on any machine without an API key.
- **Hybrid parser.** Baseline (pdfplumber), Docling, and Hybrid share one output
  schema (`PageElement -> ParsedChunk`). Hybrid is the default: Docling owns
  reading order/headings/lists/captions while Baseline backfills weak pages and
  materially richer table extraction.
- **Honest benchmark.** 30 committed questions across 5 categories (incl. 5
  adversarial/abstention), committed before results; raw outputs and failures are
  kept. Manual metrics start blank for a human reviewer and are filled for
  `run_001` in `results/run_001/manual_scoring.md` ? never auto-filled.
- **Behaviour tests.** The offline test suite pins the parts that matter
  (schemas, chunking, scoring, abstention, grounding) and runs quickly.
- **Coherent module boundaries.** `packages/core` is importable and unit-tested
  independently of FastAPI/Next.js; the API is a thin shell over it.

## What did not work / was deferred

- **Docling version sensitivity.** Docling's document API has changed across
  releases. The Hybrid path is defensive: it lets Docling provide structure but
  falls back to Baseline when pages are weak or native failures such as
  `std::bad_alloc` occur. Raw Docling diagnostics should still be re-validated
  against the installed version.
- **Page-band auto-fill not implemented.** `expected_sources.csv` leaves pages
  blank by design; `citation_page_match` therefore measures document-level hits
  unless a human (or a future post-parse mapper) fills pages.
- **Dense-only retrieval.** BM25/rerank is scaffolded in config and filter
  plumbing but not wired; keyword-heavy queries will underperform.
- **No LLM-as-judge.** Ragas/DeepEval are documented as optional; only
  deterministic metrics are computed automatically.

## Honest engineering trade-offs

- **Offline extractive over a local LLM.** A local generative model would read
  better but is non-deterministic and heavy; extractive grounding is ugly-prose
  but bulletproof on the "no citation, no claim" rule. For a compliance demo,
  the latter is the right default.
- **JSON-backed registry over a database.** Keeps the stack dependency-light for a
  demo; the `DocumentRegistry` interface is small enough to swap for SQLite/Postgres.
- **Next.js over Streamlit.** More code, but signals full-stack capability and
  gives the citation/evidence UX a real interface rather than a form dump. The
  API contract (`lib/types.ts`) mirrors the Pydantic models 1:1.

## What I would improve next (prioritised)

1. **BM25 + dense retrieval** with cross-encoder rerank ? biggest score lift.
2. **Bounding-box provenance in the UI** ? Docling already carries `bbox`; render
   the highlighted source span on the citation card.
3. **Page-band auto-fill** ? post-parse, locate each `expected_evidence_snippet`
   in the parsed chunks and backfill pages so `citation_page_match` is automatic.
4. **A real LLM-judge lane** behind the existing optional metrics, keeping
   deterministic metrics as the always-on baseline.
5. **Cross-document entity linking** for KYC (controller <-> company <-> filings).
6. **Automated table-structure scoring** against a DocLayNet sample.

## Risks to flag to a reviewer

- Verify the Docling/Hybrid adapters against your installed version before
  trusting parser metrics.
- Follow `docs/OPERATIONS.md` to reproduce `run_001`; do not treat the sample
  report as a measured result.
- On Python 3.13/3.14 Docling/torch wheels are missing ? use 3.11/3.12.
