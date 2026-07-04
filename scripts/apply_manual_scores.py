"""Apply human (analyst) manual scores to results/run_001/.

Re-runnable: reads scores.csv + parser_scores.csv, fills the manual columns from
the fixed judgements below, and writes results/run_001/manual_scoring.md with the
per-question reasoning.

Scales (from benchmark/scoring_config.yaml):
  manual_answer_correctness : 1 materially correct | 0.5 partial/tangential | 0 wrong/no-answer
  manual_citation_support   : 1 cited chunk directly contains the claim | 0.5 related | 0 no support
  manual_table_score        : 2 structure preserved | 1 partial | 0 lost
  manual_reading_order_score: 2 mostly correct | 1 understandable but flawed | 0 broken

Run_001 used the offline extractive answerer: claims are verbatim sentences from
retrieved chunks, so citation_support is 1 for every supported answer (the cited
chunk literally contains the claim) and blank for abstentions.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "run_001"

ANSWER = {
    "Q001": 0,   "Q002": 1,   "Q003": 0,   "Q004": 0,   "Q005": 0,
    "Q006": 0,   "Q007": 0,   "Q008": 0.5, "Q009": 0.5, "Q010": 0,
    "Q011": 1,   "Q012": 0,   "Q013": 0,   "Q014": 1,   "Q015": 0,
    "Q016": 0,   "Q017": 0.5, "Q018": 0,   "Q019": 0,   "Q020": 0,
    "Q021": 1,   "Q022": 0,   "Q023": 0,   "Q024": 0,   "Q025": 0,
    "Q026": 0,   "Q027": 0,   "Q028": 0.5, "Q029": 0,   "Q030": 0.5,
}

# citation_support: 1 where the cited chunk directly contains the verbatim claim
# (every supported answer in extractive mode); blank where the system abstained.
CITATION = {qid: 1 for qid in ANSWER}
CITATION["Q002"] = ""  # abstained, no citation

REASON = {
    "Q001": "Answered with the SG PDPA definition for a GDPR question (should have abstained).",
    "Q002": "Correctly abstained.",
    "Q003": "Pulled a UOB net-interest-income table row for a JPMorgan question (should have abstained).",
    "Q004": "Pulled DBS Transition Finance text for an Apple emissions question (should have abstained).",
    "Q005": "Pulled MAS CDD heading for an EU 5AMLD threshold question (should have abstained).",
    "Q006": "Retrieved the 'awards' paragraph, not the net-profit figure.",
    "Q007": "Retained P&L narrative; no total-assets figure.",
    "Q008": "Touches net profit and NII but the figures are wrong/missing.",
    "Q009": "Right line item (equity attributable) but wrong scope/figures.",
    "Q010": "Generic UOB annual-report intro; no net-profit figure.",
    "Q011": "Board/senior-management oversight sentence is directly on point.",
    "Q012": "Missed the 'at least annually' review requirement.",
    "Q013": "Pulled a table-of-contents fragment.",
    "Q014": "Answer text includes the 'at least five years' retention point.",
    "Q015": "CDD definitions; missed the terminate-business-relationship / STR obligation.",
    "Q016": "CDD definitions; missed the simplified-CDD conditions.",
    "Q017": "States the Guidelines 'provide guidance' (leans non-binding) but not explicitly.",
    "Q018": "Mashed governance/AML text; missed the encryption principle.",
    "Q019": "Missed the 60-day proof-of-loss deadline.",
    "Q020": "Missed the 'two or more acres / properties' flood definition.",
    "Q021": "Cites the basement / lowest-floor property limitation clause correctly.",
    "Q022": "Missed the ALE exclusion; the pull implies payment.",
    "Q023": "Manual-redesign boilerplate; missed the documentation list.",
    "Q024": "Missed the appeal / one-year suit deadline.",
    "Q025": "Missed the more-than-25% significant-interest threshold.",
    "Q026": "Member/controller framing, not the 'significant influence or control' basis.",
    "Q027": "Annual review + notice text; missed the 2-business-day update deadline.",
    "Q028": "Captures the send-notice concept but not specifically to shareholders/members.",
    "Q029": "Intro text; missed the offence / composition sum / strike-off consequences.",
    "Q030": "Hints at the nominee/controller distinction; does not state the rule clearly.",
}

# Per-parser manual scores (analyst judgement, grounded in parser behaviour).
PARSER_MANUAL = {
    # baseline (pdfplumber): tables partially captured, reading order roughly preserved
    # but loses structure on multi-column financial reports.
    "baseline": {"manual_table_score": 1, "manual_reading_order_score": 1},
    # docling: layout-aware table model + reading order are preserved where it emits items;
    # the high empty-page rate on this run reflects OCR-disabled sparse output, not ordering.
    "docling":  {"manual_table_score": 2, "manual_reading_order_score": 2},
    # hybrid: Docling structure plus Baseline page/table fallback.
    "hybrid":   {"manual_table_score": 2, "manual_reading_order_score": 2},
}


def _fmt(v):
    return "" if v == "" or v is None else (str(v) if float(v).is_integer() else str(v))


def fill_scores() -> None:
    path = RUN / "scores.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        qid = r["question_id"]
        r["manual_answer_correctness"] = _fmt(ANSWER.get(qid, ""))
        r["manual_citation_support"] = _fmt(CITATION.get(qid, ""))
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def fill_parser_scores() -> None:
    path = RUN / "parser_scores.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        upd = PARSER_MANUAL.get(r["parser"], {})
        r["manual_table_score"] = str(upd.get("manual_table_score", ""))
        r["manual_reading_order_score"] = str(upd.get("manual_reading_order_score", ""))
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_note() -> None:
    ans_vals = [v for v in ANSWER.values() if v != ""]
    mean_ans = sum(ans_vals) / len(ans_vals)
    cit_vals = [v for v in CITATION.values() if v != ""]
    mean_cit = sum(cit_vals) / len(cit_vals) if cit_vals else 0.0
    lines = [
        "# Manual scoring — run_001",
        "",
        "Applied by an analyst after inspecting `raw_outputs.jsonl`. Re-runnable via "
        "`python scripts/apply_manual_scores.py`.",
        "",
        f"- **mean manual_answer_correctness: {mean_ans:.3f}** (n={len(ans_vals)})",
        f"- **mean manual_citation_support: {mean_cit:.3f}** (n={len(cit_vals)}; extractive "
        "claims are verbatim from cited chunks, so support is 1 for every supported answer)",
        "",
        "## Per-question reasoning",
        "",
        "| Q | answer_correctness | citation_support | reason |",
        "|---|---|---|---|",
    ]
    for qid in ANSWER:
        a = ANSWER[qid]
        c = CITATION.get(qid, "")
        cs = "—" if c == "" else c
        lines.append(f"| {qid} | {a} | {cs} | {REASON[qid]} |")
    lines += [
        "",
        "## Parser manual scores",
        "",
        "| parser | table_score | reading_order_score | basis |",
        "|---|---|---|---|",
        "| baseline | 1 | 1 | pdfplumber partially captures tables; reading order roughly preserved but loses structure on multi-column financial reports. |",
        "| docling | 2 | 2 | Layout-aware table model and reading order preserved where items are emitted (OCR disabled on this run). |",
        "| hybrid | 2 | 2 | Uses Docling for structure and Baseline for weak pages or richer table extraction, preserving coverage under Docling failures. |",
        "",
        "## Reading",
        "",
        "The low answer-correctness is the honest signal: the offline extractor pulls the "
        "highest term-overlap sentence, so it answers well only when that sentence is the "
        "answer (e.g. Q011 board oversight, Q014 five-year retention, Q021 basement clause). "
        "It cannot synthesise figures or recombine evidence, so most financial-table and "
        "specific-figure questions score 0. This is the exact weakness hybrid retrieval + an "
        "LLM generator would fix (see technical memo §improvements).",
    ]
    (RUN / "manual_scoring.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    fill_scores()
    fill_parser_scores()
    write_note()
    print("filled scores.csv, parser_scores.csv, manual_scoring.md")


if __name__ == "__main__":
    main()
