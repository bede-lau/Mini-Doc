"use client";

import { useAppState } from "@/components/AppState";
import { api } from "@/lib/api";
import { Button, Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";

type ReportType =
  | "kyc_beneficial_ownership"
  | "technology_risk_compliance"
  | "insurance_claims_review"
  | "general_compliance_intelligence";

const REPORT_TYPES = [
  { value: "kyc_beneficial_ownership", label: "KYC / Beneficial Ownership Brief" },
  { value: "technology_risk_compliance", label: "Technology Risk Compliance Brief" },
  { value: "insurance_claims_review", label: "Insurance Claims Review" },
  { value: "general_compliance_intelligence", label: "General Compliance Intelligence Review" },
] as const;

export default function ReportsPage() {
  const { reports } = useAppState();
  const { type, report, loading, error, setType, generate } = reports;

  function downloadMarkdown() {
    if (!report) return;
    const blob = new Blob([report.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.report_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function downloadPdf() {
    if (!report) return;
    const a = document.createElement("a");
    a.href = api.reportDownloadUrl(report);
    a.download = `${report.report_id}.pdf`;
    a.click();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">Report Builder</h1>
        <p className="text-sm text-stone-500">
          Generate an audit-ready compliance report with a professional PDF export.
        </p>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="mb-1 block text-xs uppercase tracking-wide text-stone-500">Report type</span>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as ReportType)}
              className="rounded-md border border-rule bg-stone-50 px-3 py-2 text-sm outline-none focus:border-emerald-600 focus:bg-white"
            >
              {REPORT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={generate} disabled={loading}>
            Generate
          </Button>
        </div>
      </Card>

      {loading && <Spinner label="Running grounded QA across report sections…" />}
      {error && <ErrorBox message={error} />}

      {report ? (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-rule bg-stone-50 px-4 py-2">
            <div>
              <span className="mono block text-xs text-stone-500">{report.report_id}</span>
              <span className="text-xs text-stone-400">Professional PDF generated on the backend</span>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={downloadMarkdown}>
                Download .md
              </Button>
              <Button onClick={downloadPdf}>
                Download PDF
              </Button>
            </div>
          </div>
          <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap px-4 py-4 text-[13px] leading-relaxed text-stone-800">
            {report.markdown}
          </pre>
        </Card>
      ) : (
        !loading && !error && <EmptyState>Pick a report type and generate.</EmptyState>
      )}
    </div>
  );
}
