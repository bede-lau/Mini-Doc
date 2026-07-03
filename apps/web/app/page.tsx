"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentMeta } from "@/lib/types";
import { Button, Card, EmptyState, ErrorBox, Spinner, StatusBadge } from "@/components/ui";

export default function LibraryPage() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.documents();
      setDocs(r.documents);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onUpload(file: File) {
    setBusy("upload");
    setError(null);
    try {
      await api.ingest(file);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function onParse(parser: "baseline" | "docling") {
    setBusy(`parse:${parser}`);
    setError(null);
    try {
      await api.parse(parser);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function onIndex() {
    setBusy("index");
    setError(null);
    try {
      await api.index("any");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Document Library</h1>
          <p className="text-sm text-stone-500">
            Ingest, parse, and index the public document bundle. Everything is local.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-rule px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100">
            Upload PDF
            <input
              type="file"
              accept="application/pdf"
              className="hidden"
              disabled={!!busy}
              onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
            />
          </label>
          <Button variant="ghost" disabled={!!busy} onClick={() => onParse("baseline")}>
            Parse baseline
          </Button>
          <Button variant="ghost" disabled={!!busy} onClick={() => onParse("docling")}>
            Parse docling
          </Button>
          <Button disabled={!!busy} onClick={onIndex}>
            Index
          </Button>
        </div>
      </div>

      {busy && <Spinner label={`Working: ${busy}…`} />}
      {error && <ErrorBox message={error} />}

      <Card className="overflow-hidden">
        {loading ? (
          <Spinner label="Loading documents…" />
        ) : docs.length === 0 ? (
          <EmptyState>
            No documents yet. Run the quickstart: download docs, then parse &amp; index from the API or CLI.
          </EmptyState>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-rule bg-stone-50 text-left text-xs uppercase tracking-wide text-stone-500">
              <tr>
                <th className="px-4 py-2 font-medium">Document</th>
                <th className="px-4 py-2 font-medium">Domain</th>
                <th className="px-4 py-2 font-medium">Parser</th>
                <th className="px-4 py-2 font-medium">Pages</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">SHA256</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.document_id} className="border-b border-rule last:border-0">
                  <td className="px-4 py-2">
                    <div className="font-medium text-ink">{d.filename}</div>
                    {d.source_url && (
                      <a
                        href={d.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-stone-400 hover:text-emerald-700"
                      >
                        source ↗
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-2 text-stone-600">{d.domain}</td>
                  <td className="px-4 py-2 text-stone-600">{d.parser}</td>
                  <td className="mono px-4 py-2 text-stone-600">{d.page_count}</td>
                  <td className="px-4 py-2"><StatusBadge status={d.parse_status} /></td>
                  <td className="mono px-4 py-2 text-xs text-stone-400">
                    {(d.sha256 || "").slice(0, 12)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
