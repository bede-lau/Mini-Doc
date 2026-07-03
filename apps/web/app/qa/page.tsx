"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Answer as AnswerT } from "@/lib/types";
import { Button, Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";

const SUGGESTED = [
  "Who qualifies as a registrable controller?",
  "What are the key expectations around technology risk governance?",
  "What documentation is required to file a flood claim?",
  "What were DBS net earnings in 2025?",
];

export default function QaPage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerT | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showChunks, setShowChunks] = useState(false);

  async function ask(q?: string) {
    const query = (q ?? question).trim();
    if (!query) return;
    setQuestion(query);
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await api.ask(query));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const typeStyle: Record<string, string> = {
    supported: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    insufficient_evidence: "bg-amber-50 text-amber-700 ring-amber-200",
    conflicting_evidence: "bg-red-50 text-red-700 ring-red-200",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">Evidence Q&amp;A</h1>
        <p className="text-sm text-stone-500">
          Every claim is cited to a source file and page. The system abstains when evidence is insufficient.
        </p>
      </div>

      <Card className="p-4">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="Ask a question grounded in the indexed documents…"
            className="flex-1 rounded-md border border-rule bg-stone-50 px-3 py-2 text-sm outline-none focus:border-emerald-600 focus:bg-white"
          />
          <Button onClick={() => ask()} disabled={loading}>
            Ask
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTED.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="rounded-full border border-rule px-3 py-1 text-xs text-stone-600 hover:bg-stone-100"
            >
              {s}
            </button>
          ))}
        </div>
      </Card>

      {loading && <Spinner label="Retrieving and grounding…" />}
      {error && <ErrorBox message={error} />}

      {answer && (
        <div className="space-y-4">
          <Card className="p-4">
            <div className="mb-2 flex items-center gap-2">
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${typeStyle[answer.answer_type]}`}>
                {answer.answer_type.replace(/_/g, " ")}
              </span>
            </div>
            <p className="text-[15px] leading-relaxed text-ink">{answer.answer}</p>
          </Card>

          {answer.claims.length > 0 && (
            <Card className="p-4">
              <h2 className="mb-2 text-sm font-semibold text-ink">Claims &amp; citations</h2>
              <ul className="space-y-2">
                {answer.claims.map((c) => (
                  <li key={c.claim_id} className="rounded-md border border-rule bg-stone-50 p-3 text-sm">
                    <p className="text-ink">{c.claim_text}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {c.citations.map((ct, i) => (
                        <span key={i} className="mono rounded bg-white px-2 py-0.5 text-[11px] text-stone-600 ring-1 ring-rule">
                          {ct.filename} · p.{ct.page}
                          {ct.section ? ` · ${ct.section}` : ""}
                        </span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card className="p-4">
            <button
              onClick={() => setShowChunks((v) => !v)}
              className="text-xs font-medium text-stone-500 hover:text-stone-800"
            >
              {showChunks ? "Hide" : "Show"} retrieved chunks ({answer.retrieved_chunks.length})
            </button>
            {showChunks && (
              <ul className="mt-3 space-y-2">
                {answer.retrieved_chunks.map((h) => (
                  <li key={h.chunk_id} className="rounded-md border border-rule p-3 text-xs">
                    <div className="mono mb-1 flex items-center justify-between text-stone-500">
                      <span>{h.filename} · p.{h.page_start}</span>
                      <span>score {h.score.toFixed(3)}</span>
                    </div>
                    <p className="text-stone-700">{h.chunk_text.slice(0, 280)}{h.chunk_text.length > 280 ? "…" : ""}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}

      {!answer && !loading && !error && (
        <EmptyState>Ask a question to see a cited answer or an honest abstention.</EmptyState>
      )}
    </div>
  );
}
