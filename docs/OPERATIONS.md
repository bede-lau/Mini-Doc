# Operations Runbook

This runbook covers the reproducible local workflow for Mini-Doc: prepare
the environment, ingest documents, parse/index them, run tests, run the benchmark,
and record the remaining human-review steps.

## Prerequisites

- Python 3.11 or 3.12. Avoid Python 3.13/3.14 because Docling/Torch wheels may be unavailable.
- Docker Desktop for Qdrant.
- A local virtual environment, for example:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

## Install

```powershell
pip install -r services/api/requirements.txt
pip install -e .
```

The editable install makes `packages.core` and `services` importable from scripts,
tests, and the API service.

## Start Qdrant

```powershell
docker compose up -d qdrant
curl http://localhost:6333/collections
```

The default collection is configured by `EOS_QDRANT_COLLECTION` and defaults to
`evidenceos_chunks`.

## Configure environment

```powershell
Copy-Item .env.example .env
```

No LLM key is required. The default/offline path is deterministic and suitable for
the benchmark. To use OpenAI-compatible or Anthropic generation, set the provider,
model, and API key in `.env`; keep `EOS_FORCE_OFFLINE=true` for deterministic
benchmark runs.

## Download documents

```powershell
python scripts/download_public_docs.py
```

The script writes to `data/raw_docs/` and records status in
`data/raw_docs/_download_report.csv`. If a source blocks scripted download or is a
landing page, place the PDF manually in `data/raw_docs/` using the exact manifest
filename.

For the current document bundle, all expected filenames are listed in
`manifests/public_docs.csv`.

## Parse documents

```powershell
python scripts/parse_docs.py --parser baseline
python scripts/parse_docs.py --parser docling
```

Outputs:

- `data/parsed/{parser}/{document_id}_parsed.json`
- `data/chunks/{parser}/{document_id}.jsonl`
- `data/parsed/_parse_metrics.jsonl`

Docling is configured for the bundled embedded-text PDFs with OCR disabled to
avoid local CPU/Windows memory pressure while preserving structured layout/table
extraction where available.

## Index documents

```powershell
python scripts/index_docs.py --parser docling
```

Expected successful local run for the current bundle: 1,735 Docling chunks indexed
into Qdrant.

## Run tests

```powershell
pytest -q
```

Current expected result: 30 passing tests.

## Run benchmark

Benchmark integrity depends on committing the fixed question/scoring sources
before committing results. The existing history preserves that ordering.

```powershell
python scripts/run_benchmark.py --run-id run_001
```

The run writes:

- `results/run_001/summary.md`
- `results/run_001/scores.csv`
- `results/run_001/parser_scores.csv`
- `results/run_001/raw_outputs.jsonl`
- `results/run_001/retrieved_chunks.jsonl`
- `results/run_001/environment.txt`
- `results/run_001/run_config.yaml`

The current committed `run_001` summary reports:

| Metric | Value |
|---|---:|
| Questions | 30 |
| hit_at_1 | 0.6000 |
| recall_at_3 | 0.7333 |
| recall_at_5 | 0.7667 |
| MRR | 0.6750 |
| citation_page_match | 0.7000 |
| abstention_correctness | 0.8667 |
| insufficient_evidence answers | 1 |
| unsupported_claim_total (proxy) | 0 |

## Manual review still required

The following fields require human judgement and must not be auto-filled:

- `results/run_001/scores.csv`
  - `manual_answer_correctness`
  - `manual_citation_support`
- `results/run_001/parser_scores.csv`
  - `manual_table_score`
  - `manual_reading_order_score`

Use `benchmark/scoring_config.yaml` for scoring scales.

## Run the app

Backend:

```powershell
uvicorn services.api.main:app --reload
```

Frontend:

```powershell
cd apps/web
npm install
npm run dev
```

Smoke-test:

1. Library lists the documents and status/page/SHA metadata.
2. Q&A returns cited answers for in-scope questions and abstains out of scope.
3. Reports generate a compliance review with an evidence table.
4. Benchmark page can show/run `run_001` and display metrics.

## Git workflow for benchmark integrity

1. Commit benchmark questions, expected answers/sources, scoring config, scoring
   code, and benchmark runner before any result files.
2. Run the benchmark.
3. Force-add and commit only `results/run_001/` as the results commit.
4. Do not amend the pre-results commit with outputs. If the benchmark set changes,
   create a new question set and a new run directory such as `results/run_002/`.
