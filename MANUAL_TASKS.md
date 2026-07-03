# MANUAL TASKS — what a human must do

This project is fully scaffolded and unit-tested, but several steps require a
human because they need the network, Docker, a real GPU/CPU run, or human
judgement. **Nothing here can be safely auto-run inside a sandboxed build.**
Work top to bottom.

A checklist you can copy:

```
[ ] 1.  Use Python 3.11 or 3.12 (NOT 3.13/3.14)
[ ] 2.  Install Docker Desktop and start Qdrant
[ ] 3.  Create .env (cp .env.example .env) — no key required to run
[ ] 4.  Install Python deps (pip install -r services/api/requirements.txt && pip install -e .)
[ ] 5.  Download the 9 public PDFs (script) — then fetch ACRA manually
[ ] 6.  (Optional) Add an LLM API key to .env for non-offline answers
[ ] 7.  Parse docs (baseline + docling) — first runs download models
[ ] 8.  Index docs into Qdrant — first run downloads the embedding model
[ ] 9.  Start backend + frontend; smoke-test the 4 pages
[ ] 10. Run pytest (should be 27 green)
[ ] 11. Run the benchmark → results/run_001/
[ ] 12. Fill MANUAL scoring columns in scores.csv / parser_scores.csv
[ ] 13. Make the two benchmark-integrity git commits (questions BEFORE results)
[ ] 14. Fill README result-summary + record the demo video
```

---

## 1. Use Python 3.11 or 3.12

**Why:** Docling (and its torch dependency) do not yet publish wheels for Python
3.13/3.14. The dev machine used to author this repo has 3.14, where `pip install
docling` fails.

**Do:** install Python 3.11 or 3.12, create the venv with it, e.g.:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

## 2. Docker + Qdrant

```bash
docker compose up -d qdrant
# verify: curl http://localhost:6333/collections
```

Qdrant must be reachable at `http://localhost:6333` (or set `QDRANT_URL`).
`results/` and indexing depend on it.

## 3. Environment file

```bash
cp .env.example .env
```

All values have defaults; the app runs **without any API key** (offline grounding
mode). Edit only what you want to change (timezone, chunk size, top_k, provider).

## 4. Install Python dependencies

```bash
pip install -r services/api/requirements.txt
pip install -e .     # registers packages.core + services as importable
```

This pulls `fastapi`, `pdfplumber`, `docling`, `sentence-transformers`,
`qdrant-client`, `httpx`, `tiktoken`, `pyyaml`. Large downloads (torch) are
expected.

## 5. Download the public documents

```bash
python scripts/download_public_docs.py
```

This fetches 8 of the 9 PDFs directly. **One is manual:**

- **ACRA — `acra-registrable-controllers-guidance-2025.pdf`**: the manifest URL is
  a landing page, not a PDF. Go to
  https://www.acra.gov.sg/regulations/practice-directions-registrars-interpretations-guidance/rorc-rond-rons-guidance/
  and download **"Guidance on Register of Controllers for Companies", version 2,
  issued 16 June 2025**. Save it as
  `data/raw_docs/acra-registrable-controllers-guidance-2025.pdf` (exact name).

Verify with the download report: `cat data/raw_docs/_download_report.csv`. Every
row should be `ok` (or `skipped_exists`), except ACRA which you handle by hand.

## 6. (Optional) LLM API key

The default `EOS_LLM_PROVIDER=offline` needs **no key** and is fully reproducible.
To use a real model for richer prose answers, edit `.env`:

```
EOS_LLM_PROVIDER=openai            # or "anthropic"
EOS_LLM_MODEL=gpt-4o-mini          # or claude-sonnet-5, etc.
EOS_LLM_API_KEY=sk-...             # REQUIRED for openai/anthropic
# EOS_LLM_BASE_URL=http://localhost:11434/v1   # for Ollama / local OpenAI-compatible
```

Keep `EOS_FORCE_OFFLINE=true` if you want the benchmark to stay deterministic
even with a key present.

## 7. Parse documents (downloads models on first run)

```bash
python scripts/parse_docs.py --parser baseline
python scripts/parse_docs.py --parser docling
```

The first Docling run downloads layout/OCR models (~hundreds of MB) to the HF
cache. Outputs: `data/parsed/{parser}/{doc}_parsed.json`,
`data/chunks/{parser}/{doc}.jsonl`, metrics in `data/parsed/_parse_metrics.jsonl`.

## 8. Index into Qdrant (downloads embedding model on first run)

```bash
python scripts/index_docs.py --parser docling
```

First run downloads `BAAI/bge-small-en-v1.5` (~130 MB). Confirms `total_points`.

## 9. Start the app and smoke-test

```bash
uvicorn services.api.main:app --reload     # http://localhost:8000  (docs: /docs)
cd apps/web && npm install && npm run dev  # http://localhost:3000
```

Manually verify each page works against real data:
- **Library**: docs listed with status/pages/SHA; Parse docling + Index buttons work.
- **Q&A**: ask "Who qualifies as a registrable controller?" → cited answer; ask
  something out-of-scope → "Insufficient evidence…".
- **Reports**: generate a General Compliance Intelligence Review; check the
  Evidence Table is populated and cited.
- **Benchmark**: run `run_001`; metric tiles populate.

## 10. Run the test suite

```bash
pytest -q
```

Expected: **27 passed** (schemas, chunking, scoring, qa/abstention, hashing).
These are offline and fast; they do not exercise Qdrant/Docling.

## 11. Run the benchmark

```bash
python scripts/run_benchmark.py --run-id run_001
cat results/run_001/summary.md
```

This is the run that Commit 2 captures. Inspect `raw_outputs.jsonl` and
`retrieved_chunks.jsonl`.

## 12. Fill the MANUAL scoring columns (human judgement — never auto-filled)

Open `results/run_001/scores.csv` and fill, per question:

- `manual_answer_correctness` — 1 / 0.5 / 0 (materially correct / partial / wrong)
- `manual_citation_support` — 1 / 0.5 / 1 (direct / related / unsupported)

Open `results/run_001/parser_scores.csv` and fill:

- `manual_table_score` — 2 / 1 / 0 (structure preserved / partial / lost)
- `manual_reading_order_score` — 2 / 1 / 0 (correct / flawed / broken)

Scales are documented in `benchmark/scoring_config.yaml`.

## 13. Make the benchmark-integrity git commits (ORDER MATTERS)

If the repo is not yet git-tracked: `git init && git add . && git commit`.

Then ensure the two-step ordering is visible in history:

- **Commit 1 (questions before results):**
  ```
  git add benchmark/questions.csv benchmark/expected_answers.csv \
          benchmark/expected_sources.csv benchmark/scoring_config.yaml \
          scripts/run_benchmark.py packages/core/evaluation/
  git commit -m "test: add fixed benchmark set and scoring script"
  ```
- **Commit 2 (results after running):**
  ```
  git add results/run_001/
  git commit -m "eval: add first reproducible benchmark run"
  ```

This ordering is the proof of benchmark integrity — do not reorder it. To change
the question set later, use `benchmark_v2/` and `results/run_002/`.

## 14. Finish the README + demo

- Paste the actual numbers from `results/run_001/summary.md` into README §12.
- Record the 5-minute demo using `examples/demo_script.md`.
- Review `examples/technical_memo.md` and adjust to match what you actually
  observed.

---

## If something breaks

- **`pydantic`/import errors at runtime** → you skipped `pip install -e .`; run it.
- **`/qa` returns 503** → Qdrant isn't up or you haven't indexed. `docker compose
  up -d qdrant` then `python scripts/index_docs.py --parser docling`.
- **`docling` install fails** → you're on Python 3.13/3.14. Use 3.11/3.12 (task 1).
- **Docling item API differs** → `docling_parser.py` is defensive but version-
  sensitive; check `doc.iterate_items` / item `.label` / `.text` / `.prov` for
  your installed version.
- **Embedding dim mismatch** → `bge-small` is 384; if you change
  `EOS_EMBEDDING_MODEL`, also set `EOS_EMBEDDING_DIM` and recreate the Qdrant
  collection (delete `data/vector_store/qdrant`).
