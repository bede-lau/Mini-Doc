# Manual scoring — run_001

Applied by an analyst after inspecting `raw_outputs.jsonl`. Re-runnable via `python scripts/apply_manual_scores.py`.

- **mean manual_answer_correctness: 0.217** (n=30)
- **mean manual_citation_support: 1.000** (n=29; extractive claims are verbatim from cited chunks, so support is 1 for every supported answer)

## Per-question reasoning

| Q | answer_correctness | citation_support | reason |
|---|---|---|---|
| Q001 | 0 | 1 | Answered with the SG PDPA definition for a GDPR question (should have abstained). |
| Q002 | 1 | — | Correctly abstained. |
| Q003 | 0 | 1 | Pulled a UOB net-interest-income table row for a JPMorgan question (should have abstained). |
| Q004 | 0 | 1 | Pulled DBS Transition Finance text for an Apple emissions question (should have abstained). |
| Q005 | 0 | 1 | Pulled MAS CDD heading for an EU 5AMLD threshold question (should have abstained). |
| Q006 | 0 | 1 | Retrieved the 'awards' paragraph, not the net-profit figure. |
| Q007 | 0 | 1 | Retained P&L narrative; no total-assets figure. |
| Q008 | 0.5 | 1 | Touches net profit and NII but the figures are wrong/missing. |
| Q009 | 0.5 | 1 | Right line item (equity attributable) but wrong scope/figures. |
| Q010 | 0 | 1 | Generic UOB annual-report intro; no net-profit figure. |
| Q011 | 1 | 1 | Board/senior-management oversight sentence is directly on point. |
| Q012 | 0 | 1 | Missed the 'at least annually' review requirement. |
| Q013 | 0 | 1 | Pulled a table-of-contents fragment. |
| Q014 | 1 | 1 | Answer text includes the 'at least five years' retention point. |
| Q015 | 0 | 1 | CDD definitions; missed the terminate-business-relationship / STR obligation. |
| Q016 | 0 | 1 | CDD definitions; missed the simplified-CDD conditions. |
| Q017 | 0.5 | 1 | States the Guidelines 'provide guidance' (leans non-binding) but not explicitly. |
| Q018 | 0 | 1 | Mashed governance/AML text; missed the encryption principle. |
| Q019 | 0 | 1 | Missed the 60-day proof-of-loss deadline. |
| Q020 | 0 | 1 | Missed the 'two or more acres / properties' flood definition. |
| Q021 | 1 | 1 | Cites the basement / lowest-floor property limitation clause correctly. |
| Q022 | 0 | 1 | Missed the ALE exclusion; the pull implies payment. |
| Q023 | 0 | 1 | Manual-redesign boilerplate; missed the documentation list. |
| Q024 | 0 | 1 | Missed the appeal / one-year suit deadline. |
| Q025 | 0 | 1 | Missed the more-than-25% significant-interest threshold. |
| Q026 | 0 | 1 | Member/controller framing, not the 'significant influence or control' basis. |
| Q027 | 0 | 1 | Annual review + notice text; missed the 2-business-day update deadline. |
| Q028 | 0.5 | 1 | Captures the send-notice concept but not specifically to shareholders/members. |
| Q029 | 0 | 1 | Intro text; missed the offence / composition sum / strike-off consequences. |
| Q030 | 0.5 | 1 | Hints at the nominee/controller distinction; does not state the rule clearly. |

## Parser manual scores

| parser | table_score | reading_order_score | basis |
|---|---|---|---|
| baseline | 1 | 1 | pdfplumber partially captures tables; reading order roughly preserved but loses structure on multi-column financial reports. |
| docling | 2 | 2 | Layout-aware table model and reading order preserved where items are emitted (OCR disabled on this run). |

## Reading

The low answer-correctness is the honest signal: the offline extractor pulls the highest term-overlap sentence, so it answers well only when that sentence is the answer (e.g. Q011 board oversight, Q014 five-year retention, Q021 basement clause). It cannot synthesise figures or recombine evidence, so most financial-table and specific-figure questions score 0. This is the exact weakness hybrid retrieval + an LLM generator would fix (see technical memo §improvements).
