"""Report builder.

Runs evidence-grounded QA for a small set of seed prompts per report type and
assembles a Report (data model). Every finding, fact and evidence-table row is
derived from a cited retrieved chunk, so the report inherits the grounding rules
of the QA layer. The Markdown rendering lives in renderer.py.
"""
from __future__ import annotations

import re

from packages.core.config import Settings, get_settings
from packages.core.generation.qa import qa
from packages.core.registry import DocumentRegistry
from packages.core.schemas.evidence import Answer
from packages.core.schemas.report import (
    Report,
    ReportConfig,
    ReportConflict,
    ReportFact,
    ReportFinding,
    ReportMissingItem,
    ReportRiskFlag,
    ReportSection,
    ReportType,
)
from packages.core.utils.logging import get_logger
from packages.core.utils.timeutil import now_iso

log = get_logger(__name__)

_SEED_PROMPTS: dict[str, list[str]] = {
    "kyc_beneficial_ownership": [
        "Who qualifies as a registrable controller?",
        "What is the significant interest or control threshold that triggers registration?",
        "What are the KYC and beneficial ownership record-keeping obligations?",
        "What are the penalties for failing to maintain a register of controllers?",
    ],
    "technology_risk_compliance": [
        "What are the key expectations around technology risk governance?",
        "What controls are required for technology risk management?",
        "Who is responsible for technology risk oversight at the board level?",
        "What are the incident reporting and resilience requirements?",
    ],
    "insurance_claims_review": [
        "What is the claims process under the flood insurance policy?",
        "What documentation is required to file a proof of loss?",
        "Does the policy cover damage that is not directly caused by flood?",
        "What are the time limits for filing a claim?",
    ],
    "general_compliance_intelligence": [
        "What are the key obligations identified across the reviewed documents?",
        "What are the highest-risk gaps in the document bundle?",
        "Which controls or governance expectations recur across documents?",
        "Where is the evidence insufficient to draw a conclusion?",
    ],
}

_REPORT_TITLES = {
    "kyc_beneficial_ownership": "KYC / Beneficial Ownership Brief",
    "technology_risk_compliance": "Technology Risk Compliance Brief",
    "insurance_claims_review": "Insurance Claims Review",
    "general_compliance_intelligence": "Compliance Intelligence Review",
}

_RISK_KEYWORDS = {
    "critical": "Critical",
    "breach": "High",
    "high": "High",
    "exposure": "High",
    "gap": "Medium",
    "risk": "Medium",
    "weak": "Medium",
    "control": "Medium",
    "missing": "Low",
}


def _risk_level(text: str) -> str:
    t = (text or "").lower()
    for kw, sev in _RISK_KEYWORDS.items():
        if kw in t:
            return sev
    return "Informational"


def _support_level(score: float) -> str:
    if score >= 0.6:
        return "direct"
    if score >= 0.45:
        return "partial"
    return "weak"


def _finding_status(answer_type: str) -> str:
    return {
        "supported": "Supported",
        "insufficient_evidence": "Insufficient Evidence",
        "conflicting_evidence": "Conflicting Evidence",
    }.get(answer_type, "Partial")


def build_report(
    report_type: ReportType,
    retriever,
    registry: DocumentRegistry | None = None,
    settings: Settings | None = None,
) -> Report:
    s = settings or get_settings()
    reg = registry or DocumentRegistry(settings=s)
    prompts = _SEED_PROMPTS.get(report_type, _SEED_PROMPTS["general_compliance_intelligence"])

    findings: list[ReportFinding] = []
    facts: list[ReportFact] = []
    evidence_rows: list[dict] = []
    retrieval_log: list[dict] = []
    missing: list[ReportMissingItem] = []
    conflicts: list[ReportConflict] = []
    risk_flags: list[ReportRiskFlag] = []

    supported = 0
    abstained = 0

    for idx, prompt in enumerate(prompts, start=1):
        answer: Answer = qa(prompt, retriever, settings=s)
        hits_by_id = {h.chunk_id: h for h in answer.retrieved_chunks}
        retrieval_log.append({
            "section": prompt,
            "top_chunks": [
                {"chunk_id": h.chunk_id, "filename": h.filename, "page": h.page_start, "score": round(h.score, 4)}
                for h in answer.retrieved_chunks[:5]
            ],
        })

        if answer.answer_type == "insufficient_evidence":
            abstained += 1
            missing.append(ReportMissingItem(
                missing_item=prompt,
                why_it_matters="The reviewed documents did not contain sufficient evidence to answer.",
                required_source="Add a source that addresses this question.",
                impact="Cannot draw a defensible conclusion for this section.",
            ))
            findings.append(ReportFinding(
                finding_id=f"F-{idx:03d}",
                title=prompt[:90],
                status="Insufficient Evidence",
                risk_level="Low",
                claim="Insufficient evidence in the reviewed documents.",
                evidence="",
                source_filename="",
                analyst_note="Abstained; no chunk passed the grounding threshold.",
            ))
            continue

        if answer.answer_type == "conflicting_evidence":
            conflicts.append(ReportConflict(
                conflict_id=f"C-{idx:03d}",
                conflict=prompt,
                source_a=answer.citations[0].filename if answer.citations else "",
                source_b=answer.citations[1].filename if len(answer.citations) > 1 else "",
                resolution_status="Open",
            ))

        supported += 1
        first_claim = answer.claims[0].claim_text if answer.claims else answer.answer
        first_hit = None
        if answer.claims and answer.claims[0].citations:
            first_hit = hits_by_id.get(answer.claims[0].citations[0].chunk_id)
        sev = _risk_level(first_claim + " " + prompt)

        findings.append(ReportFinding(
            finding_id=f"F-{idx:03d}",
            title=prompt[:90],
            status=_finding_status(answer.answer_type),
            risk_level=sev,  # type: ignore[arg-type]
            claim=first_claim,
            evidence=(first_hit.chunk_text[:300] if first_hit else (first_claim[:300])),
            source_filename=(first_hit.filename if first_hit else ""),
            page=(first_hit.page_start if first_hit else None),
            section=(first_hit.section if first_hit else None),
            analyst_note="Auto-generated from grounded QA; verify before external use.",
        ))

        if sev != "Informational":
            risk_flags.append(ReportRiskFlag(
                risk_id=f"R-{idx:03d}",
                risk=f"{prompt} — relevant risk indicator identified.",
                severity=sev,  # type: ignore[arg-type]
                evidence=(first_hit.chunk_text[:200] if first_hit else first_claim[:200]),
                source=(first_hit.filename if first_hit else "") + (
                    f" p.{first_hit.page_start}" if first_hit else ""
                ),
                recommended_next_step="Review the cited source and confirm the risk treatment.",
            ))

        for ci, claim in enumerate(answer.claims, start=1):
            for cj, cit in enumerate(claim.citations, start=1):
                hit = hits_by_id.get(cit.chunk_id)
                score = round(hit.score, 4) if hit else 0.0
                quote = (hit.chunk_text[:240] if hit else claim.claim_text[:240])
                fid = f"F-{idx:03d}-{ci}-{cj}"
                facts.append(ReportFact(
                    fact_id=fid,
                    fact=claim.claim_text,
                    type="extracted_fact",
                    source=cit.filename,
                    page=cit.page,
                    evidence_quote=quote,
                    confidence=score,
                ))
                evidence_rows.append({
                    "Claim ID": fid,
                    "Claim": claim.claim_text,
                    "Evidence quote": quote,
                    "Source document": cit.filename,
                    "Page": cit.page,
                    "Section": cit.section or "",
                    "Support level": _support_level(score),
                    "Confidence": score,
                })

    docs = reg.list()
    inventory_rows = [
        {
            "#": i,
            "Document": d.filename,
            "Domain": d.domain,
            "Type": d.document_type,
            "Pages": d.page_count,
            "Parser": d.parser,
            "Status": d.parse_status,
            "SHA256": (d.sha256 or "")[:16],
        }
        for i, d in enumerate(docs, start=1)
    ]

    exec_summary = ReportSection(
        title="Executive Summary",
        bullets=[
            f"Documents reviewed: {len(docs)}.",
            f"Sections analysed: {len(prompts)} (supported: {supported}, insufficient: {abstained}).",
            f"Highest-risk findings: {sum(1 for r in risk_flags if r.severity in ('Critical','High'))} high/critical.",
            f"Evidence sufficiency: {supported}/{len(prompts)} sections grounded in cited evidence.",
        ],
    )
    scope = ReportSection(
        title="Scope and Limitations",
        bullets=[
            f"Included documents: {', '.join(d.filename for d in docs) or 'none indexed yet'}.",
            "Excluded documents: none on purpose.",
            "Parser policy: Hybrid uses Docling structure where available and Baseline fallback for weak pages or richer tables.",
            "Known retrieval limitations: dense embeddings only (no BM25 rerank); top_k and abstention threshold are configurable.",
            "No private/client data used — public demo data only.",
        ],
    )

    cfg = ReportConfig(
        parser="hybrid (Docling structure + Baseline fallback)",
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        embedding_model=s.embedding_model,
        vector_db="Qdrant",
        retrieval_top_k=s.top_k,
        reranking="none (dense only)",
        llm_model=("offline (extractive)" if s.effective_llm_provider == "offline" else s.llm_model),
        temperature=s.llm_temperature,
    )

    next_actions = [
        {
            "Action": f"Confirm treatment for: {r.risk[:80]}",
            "Rationale": r.recommended_next_step,
            "Evidence source": r.source,
            "Owner": "Compliance analyst",
        }
        for r in risk_flags
    ] or [{"Action": "No high-risk flags raised.", "Rationale": "Evidence was sufficient and grounded.",
           "Evidence source": "—", "Owner": "Compliance analyst"}]

    stamp = re.sub(r"[^0-9A-Za-z]", "", now_iso())[:14]
    return Report(
        report_id=f"CIR-{stamp}",
        prepared_date=now_iso(),
        document_bundle=_REPORT_TITLES.get(report_type, str(report_type)),
        documents=inventory_rows,
        executive_summary=exec_summary,
        scope=scope,
        inventory=ReportSection(
            title="Document Inventory",
            table_columns=["#", "Document", "Domain", "Type", "Pages", "Parser", "Status", "SHA256"],
            table_rows=inventory_rows,
        ),
        findings=findings,
        facts=facts,
        risk_flags=risk_flags,
        missing=missing,
        conflicts=conflicts,
        evidence_table_rows=evidence_rows,
        next_actions=next_actions,
        retrieval_log=retrieval_log,
        config=cfg,
    )
