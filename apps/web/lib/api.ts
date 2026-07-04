import type {
  Answer,
  BenchmarkSummary,
  BenchmarkRunInfo,
  DeleteDocumentResponse,
  DocumentMeta,
  IngestResponse,
  ReportResponse,
  RetrievalHit,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      detail = body.detail ? String(body.detail) : detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,

  async health(): Promise<{ status: string }> {
    return asJson(await fetch(`${BASE}/health`));
  },

  async documents(): Promise<{ documents: DocumentMeta[]; total: number }> {
    return asJson(await fetch(`${BASE}/documents`));
  },

  async deleteDocument(document_id: string): Promise<DeleteDocumentResponse> {
    return asJson(
      await fetch(`${BASE}/documents/${encodeURIComponent(document_id)}`, { method: "DELETE" }),
    );
  },

  async ingest(file: File): Promise<IngestResponse> {
    const form = new FormData();
    form.append("file", file);
    return asJson(await fetch(`${BASE}/ingest`, { method: "POST", body: form }));
  },

  async parse(parser: "baseline" | "docling" | "hybrid" = "hybrid", document_ids?: string[]) {
    return asJson(
      await fetch(`${BASE}/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parser, document_ids: document_ids ?? null }),
      }),
    );
  },

  async index(parser: "baseline" | "docling" | "hybrid" | "any" = "hybrid", document_ids?: string[]) {
    return asJson(
      await fetch(`${BASE}/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parser, document_ids: document_ids ?? null }),
      }),
    );
  },

  async search(query: string, top_k?: number, filters?: Record<string, unknown>) {
    return asJson<{ query: string; hits: RetrievalHit[]; total: number }>(
      await fetch(`${BASE}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: top_k ?? null, filters: filters ?? null }),
      }),
    );
  },

  async ask(question: string, top_k?: number, filters?: Record<string, unknown>): Promise<Answer> {
    return asJson<Answer>(
      await fetch(`${BASE}/qa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: top_k ?? null, filters: filters ?? null }),
      }),
    );
  },

  async generateReport(
    report_type: "kyc_beneficial_ownership" | "technology_risk_compliance" | "insurance_claims_review" | "general_compliance_intelligence",
  ): Promise<ReportResponse> {
    return asJson<ReportResponse>(
      await fetch(`${BASE}/reports/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_type }),
      }),
    );
  },

  reportDownloadUrl(report: ReportResponse): string {
    return `${BASE}${report.pdf_url}`;
  },

  async runBenchmark(run_id = "run_001"): Promise<BenchmarkSummary> {
    return asJson<BenchmarkSummary>(
      await fetch(`${BASE}/benchmarks/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id }),
      }),
    );
  },

  async benchmarkResults(): Promise<{ runs: BenchmarkRunInfo[] }> {
    return asJson(await fetch(`${BASE}/benchmarks/results`));
  },

  async benchmarkResult(run_id: string): Promise<BenchmarkSummary> {
    return asJson(await fetch(`${BASE}/benchmarks/results/${encodeURIComponent(run_id)}`));
  },

  async deleteBenchmarkRun(run_id: string): Promise<{ run_id: string; deleted: boolean; removed_files: string[] }> {
    return asJson(
      await fetch(`${BASE}/benchmarks/results/${encodeURIComponent(run_id)}`, { method: "DELETE" }),
    );
  },
};
