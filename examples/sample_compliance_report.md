<!--
  SAMPLE — hand-authored to illustrate the report template and grounding style.
  Figures and quotes are illustrative of the public source subject matter, not
  extracted from a live run. A real report is produced by
  POST /reports/generate and stored under results/reports/.
-->

# Compliance Intelligence Review

**Report ID:** CIR-SAMPLE-KYC
**Prepared for:** Regulated Workflow Demo
**Prepared by:** EvidenceOS Mini
**Prepared date:** 2026-07-03T22:40:00+08:00
**Document bundle:** KYC / Beneficial Ownership Brief
**Confidentiality:** Public demo data only
**Disclaimer:** This is a technical work sample using public/synthetic documents. It is not legal, financial, insurance, or regulatory advice.

## 1. Executive Summary

- Documents reviewed: 1 (ACRA Guidance on Register of Registrable Controllers).
- Sections analysed: 4 (supported: 4, insufficient: 0).
- Highest-risk findings: 1 high/critical (offence on failure to maintain register).
- Evidence sufficiency: 4/4 sections grounded in cited evidence.

## 2. Scope and Limitations

- Included documents: acra-registrable-controllers-guidance-2025.pdf.
- Excluded documents: none on purpose.
- Known extraction limitations: baseline parser loses reading order and some tables; Docling preserves structure where available.
- Known retrieval limitations: dense embeddings only (no BM25 rerank); top_k and abstention threshold are configurable.
- No private/client data used — public demo data only.

## 3. Document Inventory

| # | Document | Domain | Type | Pages | Parser | Status | SHA256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | acra-registrable-controllers-guidance-2025.pdf | kyc | guidance | 24 | docling | success | 3e23e816003959… |

## 4. Key Findings

### Finding F-001 — Who qualifies as a registrable controller
**Status:** Supported
**Risk level:** Low
**Claim:** A registrable controller is an individual or legal entity with a significant interest (more than 25% of shares or voting rights) or significant influence/control over the company.
**Evidence:** "A registrable controller… has significant interest or significant control… more than 25% of the total number of issued shares… or more than 25% of the total voting power."
**Source:** acra-registrable-controllers-guidance-2025.pdf, page 5, section Significant Interest or Control
**Analyst note:** Auto-generated from grounded QA; verify before external use.

### Finding F-002 — Significant-interest threshold
**Status:** Supported
**Risk level:** Informational
**Claim:** The significant-interest threshold is more than 25% of issued shares (excluding treasury shares) or more than 25% of total voting power.
**Evidence:** "…more than 25% of the total number of issued shares (excluding treasury shares)…"
**Source:** acra-registrable-controllers-guidance-2025.pdf, page 5
**Analyst note:** Auto-generated from grounded QA; verify before external use.

### Finding F-003 — Register maintenance duty and timing
**Status:** Supported
**Risk level:** Medium
**Claim:** A company must enter or update particulars in the Register of Registrable Controllers within 2 business days of receiving the information.
**Evidence:** "…within 2 business days after receiving the information."
**Source:** acra-registrable-controllers-guidance-2025.pdf, page 9, section Maintaining the Register
**Analyst note:** Auto-generated from grounded QA; verify before external use.

### Finding F-004 — Failure to maintain the register is an offence
**Status:** Supported
**Risk level:** High
**Claim:** Failure to keep or maintain the register is an offence under the Companies Act; ACRA may offer a composition sum in lieu of prosecution and, in serious cases, strike the company off.
**Evidence:** "…an offence under the Companies Act… composition sum in lieu of prosecution… struck off the register."
**Source:** acra-registrable-controllers-guidance-2025.pdf, page 20, section Offences and Enforcement
**Analyst note:** Auto-generated from grounded QA; verify before external use.

## 5. Extracted Facts Register

| Fact ID | Fact | Type | Source | Page | Evidence quote | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| F-001-1 | A registrable controller has significant interest or significant control. | extracted_fact | acra-registrable-controllers-guidance-2025.pdf | 5 | "…significant interest or significant control…" | 0.82 |
| F-002-1 | The threshold is more than 25% of issued shares or voting power. | extracted_fact | acra-registrable-controllers-guidance-2025.pdf | 5 | "…more than 25%…" | 0.78 |
| F-003-1 | The register must be updated within 2 business days. | extracted_fact | acra-registrable-controllers-guidance-2025.pdf | 9 | "…within 2 business days…" | 0.71 |
| F-004-1 | Failure to maintain the register is an offence; composition sum or strike-off. | extracted_fact | acra-registrable-controllers-guidance-2025.pdf | 20 | "…offence under the Companies Act…" | 0.69 |

## 6. Risk Flags

| Risk ID | Risk | Severity | Evidence | Source | Recommended next step |
| --- | --- | --- | --- | --- | --- |
| R-004 | Failure to maintain the register — relevant risk indicator identified. | High | "…offence under the Companies Act…" | acra-registrable-controllers-guidance-2025.pdf p.20 | Review the cited source and confirm the risk treatment. |

## 7. Missing Information

_(no rows)_

> No items abstained in this sample. In a real run, questions with insufficient
> evidence appear here as Missing Information.

## 8. Contradictions and Conflicts

> No contradictions were detected within the reviewed evidence. This does not mean the document bundle is complete.

## 9. Evidence Table

| Claim ID | Claim | Evidence quote | Source document | Page | Section | Support level | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F-001-1 | A registrable controller has significant interest or significant control. | "…significant interest or significant control…" | acra-registrable-controllers-guidance-2025.pdf | 5 | Significant Interest or Control | direct | 0.82 |
| F-002-1 | The threshold is more than 25%. | "…more than 25%…" | acra-registrable-controllers-guidance-2025.pdf | 5 | Significant Interest or Control | direct | 0.78 |
| F-003-1 | Update within 2 business days. | "…within 2 business days…" | acra-registrable-controllers-guidance-2025.pdf | 9 | Maintaining the Register | partial | 0.71 |
| F-004-1 | Offence; composition sum or strike-off. | "…offence under the Companies Act…" | acra-registrable-controllers-guidance-2025.pdf | 20 | Offences and Enforcement | partial | 0.69 |

## 10. Recommended Next Actions

| Action | Rationale | Evidence source | Owner |
| --- | --- | --- | --- |
| Confirm treatment for: Failure to maintain the register… | Review the cited source and confirm the risk treatment. | acra-registrable-controllers-guidance-2025.pdf p.20 | Compliance analyst |

## Appendix A — Retrieval Log

**Section:** Who qualifies as a registrable controller?

| chunk_id | filename | page | score |
| --- | --- | --- | --- |
| acra_p5_c001 | acra-registrable-controllers-guidance-2025.pdf | 5 | 0.82 |
| acra_p6_c002 | acra-registrable-controllers-guidance-2025.pdf | 6 | 0.6 |

## Appendix B — Benchmark Run Summary

_Run `python scripts/run_benchmark.py --run-id run_001` and review results/run_001/summary.md._

## Appendix C — Model and Parser Configuration

| Setting | Value |
| --- | --- |
| parser | docling (+ baseline compared) |
| chunk_size | 700 |
| chunk_overlap | 120 |
| embedding_model | BAAI/bge-small-en-v1.5 |
| vector_db | Qdrant |
| retrieval_top_k | 8 |
| reranking | none (dense only) |
| llm_model | offline (extractive) |
| temperature | 0.0 |
