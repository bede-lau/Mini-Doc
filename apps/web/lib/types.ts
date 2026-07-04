// Types mirroring the FastAPI response models (packages/core/schemas).

export type ParseStatus = "pending" | "success" | "failed" | "partial";
export type AnswerType = "supported" | "insufficient_evidence" | "conflicting_evidence";

export interface IngestResponse {
  document_id: string;
  filename: string;
  page_count: number;
  parser: string;
  status: string;
  sha256: string;
  errors: string[];
}

export interface DocumentMeta {
  document_id: string;
  filename: string;
  domain: string;
  document_type: string;
  source_url: string | null;
  page_count: number;
  parser: "baseline" | "docling" | "hybrid" | "ocr" | "none";
  parse_started_at: string | null;
  parse_completed_at: string | null;
  parse_status: ParseStatus;
  sha256: string | null;
  errors: string[];
}

export interface DeleteDocumentResponse {
  document_id: string;
  filename: string;
  deleted: boolean;
  removed_files: string[];
  vector_delete: "success" | "skipped" | "failed";
  errors: string[];
}

export interface RetrievalHit {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_start: number;
  page_end: number;
  section: string | null;
  chunk_text: string;
  chunk_type: string;
  parser: string;
  source_parser: string | null;
  fallback_reason: string | null;
  score: number;
  source_url: string | null;
}

export interface Citation {
  filename: string;
  page: number;
  chunk_id: string;
  section: string | null;
}

export interface Claim {
  claim_id: string;
  claim_text: string;
  evidence_ids: string[];
  citations: Citation[];
}

export interface Answer {
  question: string;
  answer_type: AnswerType;
  answer: string;
  claims: Claim[];
  citations: Citation[];
  retrieved_chunks: RetrievalHit[];
}

export interface BenchmarkSummary {
  run_id: string;
  questions: number;
  output_dir: string;
  summary: {
    questions: number;
    hit_at_1: number;
    recall_at_3: number;
    recall_at_5: number;
    mrr: number;
    citation_page_match: number;
    abstention_correctness: number;
    insufficient_evidence_answers: number;
    unsupported_claim_total: number;
  };
}

export interface BenchmarkRunInfo {
  run_id: string;
  path: string;
  has_summary: boolean;
}

export interface ReportResponse {
  report_id: string;
  report_path: string;
  pdf_path: string;
  pdf_url: string;
  markdown: string;
  report: Record<string, unknown>;
}
