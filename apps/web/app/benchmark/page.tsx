"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BenchmarkSummary } from "@/lib/types";
import { Button, Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";

interface RunInfo {
  run_id: string;
  path: string;
  has_summary: boolean;
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-rule bg-stone-50 p-3">
      <div className="mono text-lg font-semibold text-ink">{value}</div>
      <div className="text-[11px] uppercase tracking-wide text-stone-500">{label}</div>
    </div>
  );
}

export default function BenchmarkPage() {
  const [runId, setRunId] = useState("run_001");
  const [latest, setLatest] = useState<BenchmarkSummary | null>(null);
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    try {
      setRuns((await api.benchmarkResults()).runs);
    } catch {
      /* runs list optional */
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runBenchmark(runId);
      setLatest(res);
      await loadRuns();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const s = latest?.summary;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Benchmark Dashboard</h1>
          <p className="text-sm text-stone-500">
            Reproducible retrieval, answer, citation, and abstention metrics. Raw outputs are saved per run.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            className="mono w-32 rounded-md border border-rule bg-stone-50 px-3 py-1.5 text-sm outline-none focus:border-emerald-600 focus:bg-white"
          />
          <Button onClick={run} disabled={loading}>
            Run benchmark
          </Button>
        </div>
      </div>

      {loading && <Spinner label="Running benchmark (this indexes + scores every question)…" />}
      {error && <ErrorBox message={error} />}

      {s && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Metric label="questions" value={s.questions} />
          <Metric label="hit@1" value={s.hit_at_1} />
          <Metric label="recall@5" value={s.recall_at_5} />
          <Metric label="MRR" value={s.mrr} />
          <Metric label="citation page match" value={s.citation_page_match} />
          <Metric label="abstention correct" value={s.abstention_correctness} />
          <Metric label="insufficient answers" value={s.insufficient_evidence_answers} />
          <Metric label="unsupported claims" value={s.unsupported_claim_total} />
        </div>
      )}

      <Card className="overflow-hidden">
        <div className="border-b border-rule px-4 py-2 text-xs font-semibold uppercase tracking-wide text-stone-500">
          Past runs
        </div>
        {runs.length === 0 ? (
          <EmptyState>No runs yet. Run the benchmark to populate results/run_001/.</EmptyState>
        ) : (
          <ul className="divide-y divide-rule">
            {runs.map((r) => (
              <li key={r.run_id} className="mono flex items-center justify-between px-4 py-2 text-sm">
                <span className="text-ink">{r.run_id}</span>
                <span className="text-stone-400">{r.path}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
