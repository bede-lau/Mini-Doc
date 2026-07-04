"""Render a Report to the compliance-ready Markdown template.

Template follows the Mini-Doc compliance-review structure (title, header
metadata, ten numbered sections, three appendices). The Evidence Table
(section 9) is always emitted.
"""
from __future__ import annotations

from packages.core.schemas.report import Report, ReportFinding


def _md_table(columns: list[str], rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for r in rows:
        body.append("| " + " | ".join(str(r.get(c, "")) for c in columns) + " |")
    return "\n".join([header, sep, *body])


def _escape(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def _render_finding(f: ReportFinding) -> str:
    source = f"**Source:** {_escape(f.source_filename)}"
    if f.source_filename:
        source += f", page {f.page}" if f.page is not None else ""
    if f.section:
        source += f", section {_escape(f.section)}"
    note = f"\n**Analyst note:** {_escape(f.analyst_note)}" if f.analyst_note else ""
    return (
        f"### Finding {f.finding_id} — {_escape(f.title)}\n"
        f"**Status:** {f.status}  \n"
        f"**Risk level:** {f.risk_level}  \n"
        f"**Claim:** {_escape(f.claim)}  \n"
        f"**Evidence:** “{_escape(f.evidence)}”  \n"
        f"{source}{note}\n"
    )


def render_report(report: Report) -> str:
    out: list[str] = []
    out.append("# Compliance Intelligence Review\n")
    out.append(f"**Report ID:** {report.report_id}  ")
    out.append(f"**Prepared for:** {report.prepared_for}  ")
    out.append(f"**Prepared by:** {report.prepared_by}  ")
    out.append(f"**Prepared date:** {report.prepared_date}  ")
    out.append(f"**Document bundle:** {report.document_bundle}  ")
    out.append(f"**Confidentiality:** {report.confidentiality}  ")
    out.append(f"**Disclaimer:** {report.disclaimer}\n")

    # 1. Executive Summary
    out.append("## 1. Executive Summary\n")
    out.extend(f"- {b}" for b in report.executive_summary.bullets)
    out.append("")

    # 2. Scope and Limitations
    out.append("## 2. Scope and Limitations\n")
    out.extend(f"- {b}" for b in report.scope.bullets)
    out.append("")

    # 3. Document Inventory
    out.append("## 3. Document Inventory\n")
    out.append(_md_table(report.inventory.table_columns, report.inventory.table_rows))
    out.append("")

    # 4. Key Findings
    out.append("## 4. Key Findings\n")
    if report.findings:
        for f in report.findings:
            out.append(_render_finding(f))
    else:
        out.append("_No findings generated._\n")

    # 5. Extracted Facts Register
    out.append("## 5. Extracted Facts Register\n")
    fact_rows = [
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
    ]
    out.append(_md_table(
        ["Fact ID", "Fact", "Type", "Source", "Page", "Evidence quote", "Confidence"], fact_rows
    ))
    out.append("")

    # 6. Risk Flags
    out.append("## 6. Risk Flags\n")
    risk_rows = [
        {
            "Risk ID": r.risk_id,
            "Risk": r.risk,
            "Severity": r.severity,
            "Evidence": r.evidence,
            "Source": r.source,
            "Recommended next step": r.recommended_next_step,
        }
        for r in report.risk_flags
    ]
    out.append(_md_table(["Risk ID", "Risk", "Severity", "Evidence", "Source", "Recommended next step"], risk_rows))
    out.append("")

    # 7. Missing Information
    out.append("## 7. Missing Information\n")
    miss_rows = [
        {
            "Missing item": m.missing_item,
            "Why it matters": m.why_it_matters,
            "Required source": m.required_source,
            "Impact": m.impact,
        }
        for m in report.missing
    ]
    out.append(_md_table(["Missing item", "Why it matters", "Required source", "Impact"], miss_rows))
    out.append("")

    # 8. Contradictions and Conflicts
    out.append("## 8. Contradictions and Conflicts\n")
    if report.conflicts:
        conf_rows = [
            {
                "Conflict ID": c.conflict_id,
                "Conflict": c.conflict,
                "Source A": c.source_a,
                "Source B": c.source_b,
                "Resolution status": c.resolution_status,
            }
            for c in report.conflicts
        ]
        out.append(_md_table(["Conflict ID", "Conflict", "Source A", "Source B", "Resolution status"], conf_rows))
    else:
        out.append(
            "> No contradictions were detected within the reviewed evidence. "
            "This does not mean the document bundle is complete."
        )
    out.append("")

    # 9. Evidence Table (mandatory)
    out.append("## 9. Evidence Table\n")
    out.append(_md_table(
        ["Claim ID", "Claim", "Evidence quote", "Source document", "Page", "Section", "Support level", "Confidence"],
        report.evidence_table_rows,
    ))
    out.append("")

    # 10. Recommended Next Actions
    out.append("## 10. Recommended Next Actions\n")
    out.append(_md_table(["Action", "Rationale", "Evidence source", "Owner"], report.next_actions))
    out.append("")

    # Appendix A — Retrieval Log
    out.append("## Appendix A — Retrieval Log\n")
    for entry in report.retrieval_log:
        out.append(f"**Section:** {entry.get('section','')}\n")
        chunks = entry.get("top_chunks", [])
        if chunks:
            out.append(_md_table(
                ["chunk_id", "filename", "page", "score"],
                [{"chunk_id": c.get("chunk_id"), "filename": c.get("filename"),
                  "page": c.get("page"), "score": c.get("score")} for c in chunks],
            ))
        else:
            out.append("_(no chunks retrieved)_")
        out.append("")

    # Appendix B — Benchmark Run Summary
    out.append("## Appendix B — Benchmark Run Summary\n")
    out.append(report.benchmark_summary or "_Run `python scripts/run_benchmark.py --run-id run_001` and review results/run_001/summary.md._")
    out.append("")

    # Appendix C — Model and Parser Configuration
    c = report.config
    out.append("## Appendix C — Model and Parser Configuration\n")
    out.append(_md_table(
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
    ))
    out.append("")

    return "\n".join(out)
