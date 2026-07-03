# Benchmark

This directory is the **fixed benchmark contract**. It is committed BEFORE any
results run. Results land separately under `results/<run_id>/`.

## Files

| File | Purpose |
|---|---|
| `questions.csv` | The fixed question set (≥30 questions across 5 categories). |
| `expected_answers.csv` | Short expected answers keyed by `question_id` (for manual compare). |
| `expected_sources.csv` | Ground-truth source document + page band per question. |
| `scoring_config.yaml` | Metric definitions, thresholds, and manual-scoring scales. |

## Benchmark integrity

> The benchmark questions, expected answers, expected sources, and scoring
> script were committed **before** the benchmark was run. Results were committed
> separately. Raw retrieved chunks and raw model outputs are included so any run
> can be inspected or rerun locally.

This is enforced by the two-commit rule:

- **Commit 1** (`test: add fixed benchmark set and scoring script`) must include
  `benchmark/questions.csv`, `benchmark/expected_answers.csv`,
  `benchmark/expected_sources.csv`, `benchmark/scoring_config.yaml`, and
  `scripts/run_benchmark.py`.
- **Commit 2** (`eval: add first reproducible benchmark run`) adds
  `results/run_001/{raw_outputs.jsonl,retrieved_chunks.jsonl,scores.csv,summary.md,environment.txt}`.

Never edit the questions after seeing results. To change the set, create a new
version directory (`benchmark_v2/`) and run it into `results/run_002/`.

## Categories (≥30 questions)

- 8 finance / regulatory
- 6 KYC / beneficial ownership
- 6 insurance claims / policy
- 5 financial table extraction
- 5 abstention / adversarial

## Running

```bash
python scripts/run_benchmark.py --run-id run_001
# inspect
cat results/run_001/summary.md
```

The runner works with no API key (deterministic offline grounding), so the run is
reproducible on any machine.
