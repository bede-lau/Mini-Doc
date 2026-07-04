# AGENTS.md ? Mini-Doc reference

Single source of truth for any agent or engineer working in this repo. Read this
first. Keep it in sync with the code.

## Project

Local-first document intelligence for regulated workflows. Pipeline:
**ingest ? parse (hybrid default; baseline/docling diagnostics) ? chunk ? index (Qdrant) ? grounded QA with
abstention ? audit-ready report ? reproducible benchmark.** No API key required
(deterministic offline grounding is the default).

## Module map

| Area | Path | Responsibility |
|---|---|---|
| Schemas (source of truth) | `packages/core/schemas/` | Pydantic models: `DocumentMeta`, `ParsedChunk`, `Answer/Claim/Citation/Evidence`, `Report*`, `api.*` |
| Config | `packages/core/config.py` | env-driven `Settings` + `get_settings()` (cached). All paths derive from `repo_root`. |
| Utils | `packages/core/utils/` | `hashing` (sha256), `tokens` (tiktoken+heuristic), `logging`, `timeutil` (tz-aware) |
| Parsers | `packages/core/parsers/` | `base` (ParserAdapter ABC, PageElement, ParseResult, factory) ? `hybrid` (Docling structure + Baseline fallback) ? `baseline` (pdfplumber) ? `docling_parser` ? `ocr` (optional) |
| Chunking | `packages/core/chunking/chunker.py` | token-aware, overlap, page/section-preserving, table-aware, never-cross-doc |
| Retrieval | `packages/core/retrieval/` | `embeddings` (SentenceTransformers, lazy) ? `qdrant_store` (upsert/search/filter/delete/count) ? `retriever` (orchestration) |
| Generation | `packages/core/generation/` | `llm_adapter` (httpx: openai/anthropic; `GROUNDING_SYSTEM_PROMPT`) ? `qa` (abstention + offline extractive + API grounding) |
| Reporting | `packages/core/reporting/` | `builder` (QA per seed prompt ? Report) ? `renderer` (Markdown template) |
| Evaluation | `packages/core/evaluation/` | `scoring` (pure metrics) ? `benchmark` (runner, writes `results/<run_id>/`) |
| Registry | `packages/core/registry.py` | JSON doc registry (`data/registry.json`) |
| Pipeline | `packages/core/pipeline.py` | shared parse?persist?chunk + index helpers (used by CLI and API) |
| API | `services/api/` | `main.py` (app) ? `state.py` (cached registry/retriever) ? `routes/{documents,qa,reports,benchmarks}.py` |
| Frontend | `apps/web/` | Next.js app router: `/` Library ? `/qa` ? `/reports` ? `/benchmark`; `lib/api.ts`, `lib/types.ts` |
| Scripts | `scripts/` | `download_public_docs`, `parse_docs`, `index_docs`, `run_benchmark` (+ `common`) |
| Tests | `tests/` | pytest behaviour suite (schemas, chunking, scoring, qa/abstention, hashing) |

## Conventions

- **Imports**: `from packages.core.x import Y`. `services` and `packages` are
  importable from the repo root (`pip install -e .` or running from root).
- **Heavy deps are lazy**: `pdfplumber`, `docling`, `sentence_transformers`,
  `qdrant_client`, `httpx` are imported inside functions/methods so the modules
  import cleanly without them (tests stay fast & offline).
- **Schemas are the contract**: never bypass Pydantic. `Claim`/`Answer` validators
  *enforce* grounding ? do not relax them.
- **Grounding rules** (non-negotiable):
  1. No citation, no claim.
  2. Below threshold or no term overlap ? `insufficient_evidence`.
  3. Separate facts from inferences.
  4. Flag conflicts; never smooth them.
  5. Always include source filename + page.
  6. Store raw retrieved chunks with every answer.
  7. Never delete failed answers from benchmark results.
- **Provider resolution**: `Settings.effective_llm_provider` forces `offline`
  when no key is set or `EOS_FORCE_OFFLINE=true`. The benchmark is reproducible
  offline.
- **Benchmark integrity**: questions (`benchmark/*.csv`) are committed BEFORE
  results (`results/run_001/`). Never edit questions after seeing results.

## Commands

```bash
# infra + deps
docker compose up -d qdrant
pip install -r services/api/requirements.txt && pip install -e .

# data pipeline
python scripts/download_public_docs.py
python scripts/parse_docs.py --parser hybrid
python scripts/index_docs.py --parser hybrid
# optional diagnostics: --parser baseline / --parser docling

# services
uvicorn services.api.main:app --reload      # backend
cd apps/web && npm install && npm run dev   # frontend

# eval
python scripts/run_benchmark.py --run-id run_001
pytest -q                                    # unit/behaviour tests
```

## Key extension points

- **New parser**: subclass `ParserAdapter` in `parsers/`, emit `PageElement`s,
  register in `parsers/base.get_parser`. Chunking/retrieval/QA pick it up
  automatically.
- **New LLM provider**: add a method to `LLMClient` + a branch in
  `Settings.effective_llm_provider`; `qa()` already degrades to extractive on
  any failure.
- **New metric**: add a pure function in `evaluation/scoring.py`, call it in
  `benchmark.run_benchmark`, add a column to the `rows.append({...})` dict.
- **New report type**: add seed prompts to `_SEED_PROMPTS` and a title in
  `reporting/builder.py`; `ReportType` + the frontend select list follow.

## Environment

See `.env.example` for all knobs. Defaults make the app run keyless and local:
Qdrant at `localhost:6333`, `bge-small-en-v1.5` (384-dim), offline LLM, chunk
700/overlap 120, top_k 8, abstention 0.35, timezone `Asia/Singapore`.


