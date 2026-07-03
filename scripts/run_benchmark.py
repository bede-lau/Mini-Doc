"""Run the benchmark and write results to results/<run_id>/.

Usage:
    python scripts/run_benchmark.py --run-id run_001

Requires the committed benchmark set (benchmark/*.csv) and an indexed Qdrant
collection. Works offline (no API key) for reproducibility.
"""
from __future__ import annotations

import argparse

from common import bootstrap

bootstrap()
from packages.core.config import get_settings  # noqa: E402
from packages.core.evaluation.benchmark import run_benchmark  # noqa: E402
from packages.core.utils.logging import get_logger  # noqa: E402

log = get_logger("benchmark")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="run_001")
    args = ap.parse_args()

    s = get_settings()
    log.info(
        "running benchmark %s (provider=%s, model=%s)",
        args.run_id, s.effective_llm_provider, s.llm_model,
    )
    result = run_benchmark(run_id=args.run_id, settings=s)
    summary = result["summary"]
    print(f"\nBenchmark {result['run_id']} complete -> {result['output_dir']}")
    print(f"questions={summary['questions']} hit@1={summary['hit_at_1']} "
          f"recall@5={summary['recall_at_5']} MRR={summary['mrr']} "
          f"abstention_correct={summary['abstention_correctness']}")
    print(f"summary: {result['output_dir']}/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
