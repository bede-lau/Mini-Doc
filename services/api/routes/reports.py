"""Audit-ready report generation route."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from packages.core.config import get_settings
from packages.core.reporting.builder import build_report
from packages.core.reporting.pdf_renderer import render_report_pdf
from packages.core.reporting.renderer import render_report
from packages.core.schemas.report import ReportType
from services.api.state import get_retriever_or_503

router = APIRouter(tags=["reports"])


class ReportRequest(BaseModel):
    report_type: ReportType = "general_compliance_intelligence"
    document_ids: list[str] | None = None


class ReportResponse(BaseModel):
    report_id: str
    report_path: str
    pdf_path: str
    pdf_url: str
    markdown: str
    report: dict


@router.post("/reports/generate", response_model=ReportResponse)
def generate(req: ReportRequest) -> ReportResponse:
    s = get_settings()
    retriever = get_retriever_or_503()
    report = build_report(req.report_type, retriever)
    markdown = render_report(report)
    out_dir = s.results_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report.report_id}.md"
    path.write_text(markdown, encoding="utf-8")
    pdf_path = out_dir / f"{report.report_id}.pdf"
    render_report_pdf(report, pdf_path)
    return ReportResponse(
        report_id=report.report_id,
        report_path=str(path),
        pdf_path=str(pdf_path),
        pdf_url=f"/reports/{report.report_id}/download",
        markdown=markdown,
        report=report.model_dump(),
    )


@router.get("/reports/{report_id}/download")
def download_report(report_id: str) -> FileResponse:
    if not report_id.startswith("CIR-") or any(ch in report_id for ch in ("/", "\\", "..")):
        raise HTTPException(status_code=400, detail="invalid report id")
    path = get_settings().results_dir / "reports" / f"{report_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="report PDF not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{report_id}.pdf",
    )


# Keep Literal import referenced for type clarity in downstream tooling.
_ = Literal
