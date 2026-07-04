"""PDF report rendering smoke tests."""
from packages.core.reporting.pdf_renderer import render_report_pdf
from packages.core.schemas.report import Report, ReportConfig, ReportFinding, ReportSection


def _sample_report() -> Report:
    return Report(
        report_id="CIR-TEST",
        prepared_date="2026-07-04",
        document_bundle="Technology Risk Compliance Brief",
        executive_summary=ReportSection(
            title="Executive Summary",
            bullets=["Evidence was reviewed and cited."],
        ),
        scope=ReportSection(
            title="Scope",
            bullets=["Public demo documents only."],
        ),
        inventory=ReportSection(
            title="Inventory",
            table_columns=["Filename", "Parser", "Pages"],
            table_rows=[{"Filename": "mas-trm.pdf", "Parser": "docling", "Pages": 57}],
        ),
        findings=[
            ReportFinding(
                finding_id="F-001",
                title="Technology risk governance",
                status="Supported",
                risk_level="Informational",
                claim="The board and senior management oversee technology risk.",
                evidence="The FI should establish governance structures and reporting lines.",
                source_filename="mas-trm.pdf",
                page=8,
                section="3.1",
            )
        ],
        evidence_table_rows=[
            {
                "Claim ID": "C-001",
                "Claim": "Governance expectation",
                "Evidence quote": "establish governance structures",
                "Source document": "mas-trm.pdf",
                "Page": 8,
                "Section": "3.1",
                "Support level": "direct",
                "Confidence": 0.9,
            }
        ],
        next_actions=[
            {
                "Action": "Review controls",
                "Rationale": "Confirm implementation",
                "Evidence source": "mas-trm.pdf",
                "Owner": "Compliance analyst",
            }
        ],
        config=ReportConfig(parser="docling", chunk_size=700, chunk_overlap=120),
    )


def test_render_report_pdf_writes_real_pdf(tmp_path):
    out = render_report_pdf(_sample_report(), tmp_path / "report.pdf")

    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000

