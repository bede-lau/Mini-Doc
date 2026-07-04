"use client";

import { useAppState } from "@/components/AppState";
import { Button, Card, EmptyState, ErrorBox, Spinner, StatusBadge } from "@/components/ui";

export default function LibraryPage() {
  const { library } = useAppState();
  const { docs, loading, error, busy, upload, deleteDocument, parse, index } = library;

  function confirmDelete(documentId: string, filename: string) {
    const ok = window.confirm(
      `Delete "${filename}" from the library?\n\nThis removes the source PDF, parsed files, chunks, registry entry, and indexed vectors when Qdrant is available.`,
    );
    if (ok) {
      deleteDocument(documentId);
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
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
            />
          </label>
          <Button variant="ghost" disabled={!!busy} onClick={parse}>
            Parse documents
          </Button>
          <Button disabled={!!busy} onClick={index}>
            Index
          </Button>
        </div>
      </div>

      {busy && <Spinner label={`Working: ${busy}...`} />}
      {error && <ErrorBox message={error} />}

      <Card className="overflow-hidden">
        {loading ? (
          <Spinner label="Loading documents..." />
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
                <th className="px-4 py-2 font-medium">Actions</th>
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
                        source
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-2 text-stone-600">{d.domain}</td>
                  <td className="px-4 py-2 text-stone-600">{d.parser}</td>
                  <td className="mono px-4 py-2 text-stone-600">{d.page_count}</td>
                  <td className="px-4 py-2"><StatusBadge status={d.parse_status} /></td>
                  <td className="mono px-4 py-2 text-xs text-stone-400">
                    {(d.sha256 || "").slice(0, 12)}...
                  </td>
                  <td className="px-4 py-2">
                    <Button
                      variant="ghost"
                      disabled={!!busy}
                      onClick={() => confirmDelete(d.document_id, d.filename)}
                    >
                      {busy === `delete:${d.document_id}` ? "Deleting" : "Delete"}
                    </Button>
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

