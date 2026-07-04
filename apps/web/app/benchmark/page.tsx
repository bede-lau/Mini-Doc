"use client";

import { useEffect } from "react";
import { useAppState } from "@/components/AppState";
import { Button, Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-rule bg-stone-50 p-3">
      <div className="mono text-lg font-semibold text-ink">{value}</div>
      <div className="text-[11px] uppercase tracking-wide text-stone-500">{label}</div>
    </div>
  );
}

export default function BenchmarkPage() {
  const { benchmark } = useAppState();
  const {
    runId,
    latest,
    runs,
    loading,
    loadingRuns,
    deletingRun,
    error,
    setRunId,
    loadRuns,
    run,
    selectRun,
    deleteRun,
  } = benchmark;

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const s = latest?.summary;

  function confirmDelete(runIdToDelete: string) {
    const ok = window.confirm(
      `Delete benchmark run "${runIdToDelete}"?\n\nThis permanently removes results/${runIdToDelete}/ (scores, raw outputs, retrieved chunks, summary, config). Source documents and indexes are untouched.`,
    );
    if (ok) {
      deleteRun(runIdToDelete);
    }
  }

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
        {loadingRuns ? (
          <div className="p-4"><Spinner label="Loading saved runs…" /></div>
        ) : runs.length === 0 ? (
          <EmptyState>No runs yet. Run the benchmark to populate results/run_001/.</EmptyState>
        ) : (
          <div className="space-y-3 p-4">
            <label className="block text-sm">
              <span className="mb-1 block text-xs uppercase tracking-wide text-stone-500">
                Select a saved run
              </span>
              <select
                value={latest?.run_id ?? ""}
                onChange={(e) => selectRun(e.target.value)}
                className="mono w-full rounded-md border border-rule bg-stone-50 px-3 py-2 text-sm outline-none focus:border-emerald-600 focus:bg-white md:w-80"
              >
                <option value="" disabled>
                  Choose a past run…
                </option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}
                  </option>
                ))}
              </select>
            </label>
            <ul className="divide-y divide-rule rounded-md border border-rule">
              {runs.map((r) => (
                <li key={r.run_id} className="mono flex items-center justify-between gap-3 px-3 py-2 text-xs">
                  <button
                    onClick={() => selectRun(r.run_id)}
                    className="text-left text-ink hover:text-emerald-700"
                  >
                    {r.run_id}
                  </button>
                  <div className="flex items-center gap-3">
                    <span className="text-stone-400">{r.path}</span>
                    <Button
                      variant="ghost"
                      onClick={() => confirmDelete(r.run_id)}
                    >
                      {deletingRun === r.run_id ? "Deleting" : "Delete"}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </div>
  );
}
