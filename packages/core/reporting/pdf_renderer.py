"""Render compliance reports as professionally formatted PDF files."""
from __future__ import annotations

from pathlib import Path
from html import escape

from packages.core.schemas.report import Report


def _plain(text: object, limit: int | None = None) -> str:
    value = str(text or "").replace("\n", " ").strip()
    if limit and len(value) > limit:
        return value[: limit - 1].rstrip() + "…"
    return escape(value)


def _report_title(report: Report) -> str:
    return report.document_bundle or "Compliance Intelligence Review"


def render_report_pdf(report: Report, path: Path) -> Path:
    """Write a styled, auditor-readable PDF for a report.

    ReportLab Platypus is used here instead of browser-printing so the backend
    produces a real downloadable PDF with page numbers, repeated table headers,
    margins, and deterministic typography.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:  # pragma: no cover - exercised by deployment smoke checks
        raise RuntimeError(
            "PDF generation requires reportlab. Install backend dependencies with "
            "`pip install -r services/api/requirements.txt`."
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Deck",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#57534E"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F766E"),
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#44403C"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Cell",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=9.2,
            textColor=colors.HexColor("#1C1917"),
        )
    )

    def para(text: object, style: str = "BodyText", limit: int | None = None) -> Paragraph:
        return Paragraph(_plain(text, limit), styles[style])

    def bullet(text: object) -> Paragraph:
        return Paragraph("• " + _plain(text), styles["BodyText"])

    def table(columns: list[str], rows: list[dict], widths: list[float] | None = None) -> Table | Paragraph:
        if not rows:
            return para("(no rows)", "Small")
        if widths is None:
            total_width = 174 * mm
            widths = [total_width / max(len(columns), 1)] * len(columns)
        data = [[para(c, "Small") for c in columns]]
        for row in rows:
            data.append([para(row.get(c, ""), "Cell", 260) for c in columns])
        tbl = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D6D3D1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAF9")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return tbl

    def on_page(canvas, doc) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#0F766E"))
        canvas.setLineWidth(0.7)
        canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#0F172A"))
        canvas.drawString(18 * mm, height - 10 * mm, "Mini-Doc")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#78716C"))
        canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=f"{report.report_id} - {_report_title(report)}",
        author="Mini-Doc",
    )

    story = [
        Spacer(1, 38),
        para("Mini-Doc", "Deck"),
        para("Compliance Intelligence Review", "CoverTitle"),
        para(_report_title(report), "Deck"),
        HRFlowable(width="65%", thickness=1, color=colors.HexColor("#0F766E"), spaceBefore=8, spaceAfter=20),
        table(
            ["Field", "Value"],
            [
                {"Field": "Report ID", "Value": report.report_id},
                {"Field": "Prepared for", "Value": report.prepared_for},
                {"Field": "Prepared by", "Value": report.prepared_by},
                {"Field": "Prepared date", "Value": report.prepared_date},
                {"Field": "Confidentiality", "Value": report.confidentiality},
                {"Field": "Disclaimer", "Value": report.disclaimer},
            ],
            [42 * mm, 112 * mm],
        ),
        PageBreak(),
    ]

    story.append(para("1. Executive Summary", "SectionTitle"))
    story.extend(bullet(b) for b in report.executive_summary.bullets)
    story.append(Spacer(1, 8))

    story.append(para("2. Scope and Limitations", "SectionTitle"))
    story.extend(bullet(b) for b in report.scope.bullets)
    story.append(Spacer(1, 8))

    story.append(para("3. Document Inventory", "SectionTitle"))
    story.append(table(report.inventory.table_columns, report.inventory.table_rows))

    story.append(para("4. Key Findings", "SectionTitle"))
    if report.findings:
        for finding in report.findings:
            story.append(
                KeepTogether(
                    [
                        para(f"{finding.finding_id}: {finding.title}", "Heading3"),
                        para(f"Status: {finding.status}    Risk: {finding.risk_level}", "Small"),
                        para(f"Claim: {finding.claim}", "BodyText"),
                        para(f"Evidence: “{finding.evidence}”", "Small"),
                        para(
                            f"Source: {finding.source_filename}"
                            + (f", page {finding.page}" if finding.page is not None else "")
                            + (f", section {finding.section}" if finding.section else ""),
                            "Small",
                        ),
                        Spacer(1, 7),
                    ]
                )
            )
    else:
        story.append(para("No findings generated.", "Small"))

    story.append(para("5. Extracted Facts Register", "SectionTitle"))
    story.append(
        table(
            ["Fact ID", "Fact", "Type", "Source", "Page", "Evidence quote", "Confidence"],
            [
                {
                    "Fact ID": f.fact_id,
                    "Fact": f.fact,
                    "Type": f.type,
                    "Source": f.source,
                    "Page": f.page if f.page is not None else "",
                    "Evidence quote": f.evidence_quote,
                    "Confidence": f.confidence,
                }
                for f in report.facts
            ],
        )
    )

    story.append(para("6. Risk Flags", "SectionTitle"))
    story.append(
        table(
            ["Risk ID", "Risk", "Severity", "Evidence", "Source", "Recommended next step"],
            [
                {
                    "Risk ID": r.risk_id,
                    "Risk": r.risk,
                    "Severity": r.severity,
                    "Evidence": r.evidence,
                    "Source": r.source,
                    "Recommended next step": r.recommended_next_step,
                }
                for r in report.risk_flags
            ],
        )
    )

    story.append(para("7. Missing Information", "SectionTitle"))
    story.append(
        table(
            ["Missing item", "Why it matters", "Required source", "Impact"],
            [
                {
                    "Missing item": m.missing_item,
                    "Why it matters": m.why_it_matters,
                    "Required source": m.required_source,
                    "Impact": m.impact,
                }
                for m in report.missing
            ],
        )
    )

    story.append(para("8. Contradictions and Conflicts", "SectionTitle"))
    if report.conflicts:
        story.append(
            table(
                ["Conflict ID", "Conflict", "Source A", "Source B", "Resolution status"],
                [
                    {
                        "Conflict ID": c.conflict_id,
                        "Conflict": c.conflict,
                        "Source A": c.source_a,
                        "Source B": c.source_b,
                        "Resolution status": c.resolution_status,
                    }
                    for c in report.conflicts
                ],
            )
        )
    else:
        story.append(para("No contradictions were detected within the reviewed evidence. This does not mean the document bundle is complete.", "Small"))

    story.append(para("9. Evidence Table", "SectionTitle"))
    story.append(
        table(
            ["Claim ID", "Claim", "Evidence quote", "Source document", "Page", "Section", "Support level", "Confidence"],
            report.evidence_table_rows,
        )
    )

    story.append(para("10. Recommended Next Actions", "SectionTitle"))
    story.append(table(["Action", "Rationale", "Evidence source", "Owner"], report.next_actions))

    story.append(PageBreak())
    story.append(para("Appendix A - Retrieval Log", "SectionTitle"))
    for entry in report.retrieval_log:
        story.append(para(f"Section: {entry.get('section', '')}", "Heading3"))
        chunks = entry.get("top_chunks", [])
        story.append(
            table(
                ["chunk_id", "filename", "page", "score"],
                [
                    {
                        "chunk_id": c.get("chunk_id"),
                        "filename": c.get("filename"),
                        "page": c.get("page"),
                        "score": c.get("score"),
                    }
                    for c in chunks
                ],
            )
        )

    story.append(para("Appendix B - Benchmark Run Summary", "SectionTitle"))
    story.append(para(report.benchmark_summary or "Run the benchmark and review results/run_001/summary.md.", "Small"))

    story.append(para("Appendix C - Model and Parser Configuration", "SectionTitle"))
    c = report.config
    story.append(
        table(
            ["Setting", "Value"],
            [
                {"Setting": "parser", "Value": c.parser},
                {"Setting": "chunk_size", "Value": c.chunk_size},
                {"Setting": "chunk_overlap", "Value": c.chunk_overlap},
                {"Setting": "embedding_model", "Value": c.embedding_model},
                {"Setting": "vector_db", "Value": c.vector_db},
                {"Setting": "retrieval_top_k", "Value": c.retrieval_top_k},
                {"Setting": "reranking", "Value": c.reranking},
                {"Setting": "llm_model", "Value": c.llm_model},
                {"Setting": "temperature", "Value": c.temperature},
            ],
            [45 * mm, 105 * mm],
        )
    )

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return path
