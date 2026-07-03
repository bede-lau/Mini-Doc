# Akro Work Trial Build Reference

## Project name
**EvidenceOS Mini: Audit-Ready Document Intelligence for Regulated Workflows**

## Objective
Build a small but credible Akro-aligned technical work sample: an app that ingests messy regulated documents, converts them into structured/citable knowledge, answers questions with evidence, generates a professional audit-ready compliance report, and benchmarks the pipeline with reproducible tests.

This is not a generic “chat with PDF” demo. It should prove:
1. document ingestion discipline;
2. layout/table/provenance awareness;
3. RAG and cited answer generation;
4. abstention when evidence is weak;
5. reproducible benchmark practice;
6. professional compliance-ready reporting.

## Why this aligns with Akro
Akro publicly positions itself as operational/data intelligence for regulated industries, using on-premise/sovereign AI workspaces to turn documents, records, and institutional knowledge into automated workflows with precision, privacy, and explainability. Their finance case study emphasizes multimodal document processing, financial table preservation, cross-document relationships, exact-source provenance, KYC reports, credit assessments, and regulatory submissions with citation trails. Their insurance and defence case studies emphasize ingest → structure → ground → reason → decide/assess, with bounding-box provenance and cited recommendations/assessments.

Sources checked July 3, 2026:
- Akro newsroom: https://www.akro.ai/newsroom/singapore-based-ai-startup-akro-raises-usd-700000-pre-seed-to-automate-data-workflows-in-regulated-industries
- Akro finance case study: https://www.akro.ai/industries/finance
- Akro insurance case study: https://www.akro.ai/industries/insurance
- Akro defence case study: https://www.akro.ai/industries/defence
- Akro careers: https://akro.ai/careers
- Akro LinkedIn full-stack AI engineer posting: https://sg.linkedin.com/jobs/view/full-stack-ai-engineer-at-akro-4235048526

## Live demo storyline
Show a regulated analyst workflow in 5 minutes:

1. Upload a document bundle.
2. The app parses documents and shows ingestion status.
3. The app extracts structured facts with provenance.
4. The analyst asks questions.
5. The app returns cited answers or abstains with “insufficient evidence.”
6. The app generates a professional compliance-ready report.
7. The app shows benchmark results and failure cases.

Suggested demo script:

> “This is a mini document-intelligence work trial for Akro. It takes public/synthetic regulated documents, turns them into structured AI-ready data, answers questions with source evidence, generates an audit-ready report, and includes a benchmark that was committed before running the tests.”

## Recommended application stack
Choose boring, inspectable tools. Do not overcomplicate.

### Frontend
- **Next.js + React + TypeScript** if there is enough time.
- **Streamlit** if speed matters more than polish.

Recommended: Next.js because Akro postings mention React/Next.js-style full-stack expectations.

### Backend
- **FastAPI** for ingestion, search, QA, report generation, benchmark runs.
- **Python 3.11+**.
- **Pydantic** for schemas.

### Document parsing
Implement two pipelines:

1. **Baseline parser**
   - PyMuPDF or pdfplumber.
   - Purpose: fast baseline, reveals limitations.

2. **Advanced parser**
   - Docling.
   - Purpose: structure-aware document conversion for tables, layout, reading order, OCR-style workflows.

Docling sources:
- Official site: https://www.docling.ai/
- Docs: https://docling-project.github.io/docling/
- GitHub: https://github.com/docling-project/docling
- LangChain integration: https://docs.langchain.com/oss/python/integrations/document_loaders/docling

Optional OCR fallback:
- Tesseract or EasyOCR only if time permits.
- Mark each OCR-derived chunk as `ocr=true` in metadata.

### Vector storage
Use one of:

1. **Qdrant in Docker** — recommended for the work trial.
2. **Postgres + pgvector** — good if you want “enterprise database” feel.
3. **Chroma** — fastest local fallback, but weaker signal.

Recommended: Qdrant because Akro postings mention vector DBs and containerization, and Qdrant runs cleanly in Docker.

Qdrant source:
- https://qdrant.tech/documentation/tutorials-develop/hybrid-search-fastembed/

### Embeddings
Use local or API-based embeddings depending on available keys.

Recommended defaults:
- `BAAI/bge-small-en-v1.5` or `BAAI/bge-base-en-v1.5` via SentenceTransformers for local reproducibility.
- Optionally add an API embedding provider behind an interface.

### LLM
Use an adapter interface so the app can swap providers.

Minimum viable:
- API LLM for answer/report generation.
- Local/offline fallback can be stubbed.

Important: The report and answers must never claim source support unless evidence chunks are present.

### Evaluation
Use a hybrid evaluation approach:

1. deterministic metrics implemented locally;
2. optional LLM-as-judge metrics via Ragas or DeepEval.

Ragas sources:
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
- https://docs.ragas.io/en/v0.1.21/concepts/metrics/

DeepEval sources:
- Faithfulness: https://deepeval.com/docs/metrics-faithfulness
- Contextual relevancy: https://deepeval.com/docs/metrics-contextual-relevancy

## Architecture

```text
apps/web                          Next.js UI
  upload page
  document library
  question answering page
  report builder page
  benchmark dashboard

services/api                      FastAPI backend
  /ingest                         upload + parse docs
  /documents                      list docs/pages/chunks
  /search                         retrieve evidence chunks
  /qa                             answer with citations
  /reports                        generate audit-ready reports
  /benchmarks/run                 run benchmark
  /benchmarks/results             view results

packages/core
  parsers/                        PyMuPDF baseline, Docling parser, OCR fallback
  chunking/                       semantic/page-aware chunking
  schemas/                        Pydantic models
  retrieval/                      Qdrant client, reranking optional
  generation/                     LLM adapter, grounded answer generator
  reporting/                      compliance report renderer
  evaluation/                     benchmark runner + scoring
  utils/                          logging, hashing, config

data/
  raw_docs/                       downloaded public PDFs
  parsed/                         parser outputs JSON/Markdown
  chunks/                         normalized chunks JSONL
  vector_store/                   Qdrant persisted or Docker volume
  benchmark/                      committed benchmark questions + expected evidence
  results/                        post-run raw outputs + scores
```

## Data model

### Document
```json
{
  "document_id": "sha256-or-uuid",
  "filename": "mas-trm-guidelines-2021.pdf",
  "domain": "finance/regulatory",
  "document_type": "regulatory_guideline",
  "source_url": "...",
  "page_count": 64,
  "parser": "docling",
  "parse_started_at": "2026-07-03T00:00:00+08:00",
  "parse_completed_at": "2026-07-03T00:01:30+08:00",
  "parse_status": "success",
  "sha256": "..."
}
```

### Chunk
```json
{
  "chunk_id": "docid_p12_c03",
  "document_id": "...",
  "filename": "mas-trm-guidelines-2021.pdf",
  "page_start": 12,
  "page_end": 13,
  "section_heading": "Technology Risk Governance",
  "chunk_text": "...",
  "chunk_type": "paragraph|table|list|figure_caption|ocr",
  "bbox": [x0, y0, x1, y1],
  "parser": "docling",
  "ocr": false,
  "token_count": 420,
  "source_url": "..."
}
```

### Evidence
```json
{
  "evidence_id": "ev_001",
  "claim_id": "claim_001",
  "chunk_id": "docid_p12_c03",
  "document_title": "MAS Technology Risk Management Guidelines",
  "filename": "mas-trm-guidelines-2021.pdf",
  "page": 12,
  "section": "Technology Risk Governance",
  "evidence_quote": "...",
  "support_level": "direct|partial|weak|contradictory",
  "confidence": 0.86
}
```

### Answer
```json
{
  "question": "What are the key expectations around technology risk governance?",
  "answer": "...",
  "answer_type": "supported|insufficient_evidence|conflicting_evidence",
  "claims": [
    {
      "claim_id": "claim_001",
      "claim_text": "The board and senior management should oversee technology risk governance.",
      "evidence_ids": ["ev_001"]
    }
  ],
  "citations": [
    {
      "filename": "mas-trm-guidelines-2021.pdf",
      "page": 12,
      "chunk_id": "docid_p12_c03"
    }
  ]
}
```

## Core grounding rules
1. No citation, no claim.
2. If top retrieved evidence has low similarity or no direct support, answer `insufficient_evidence`.
3. Separate extracted facts from inferred conclusions.
4. Flag conflicts instead of smoothing them over.
5. Always include source filename and page.
6. Store raw retrieved chunks for every answer.
7. Never delete failed answers from benchmark results.

## Document bundle
Use public documents first. Add datasets second.

### Demo document bundle
Use 6–9 documents only for the live demo.

Recommended public documents:

1. MAS Technology Risk Management Guidelines, January 2021  
   Use: technology risk control mapping and compliance Q&A.  
   URL: https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulatory-and-Supervisory-Framework/Risk-Management/TRM-Guidelines-18-January-2021.pdf

2. MAS AML/CFT Notice SFA04-N02, 30 June 2025 amendments  
   Use: precise obligation extraction.  
   URL: https://www.mas.gov.sg/-/media/amld-amendments---30-june-2025/mas-notice-sfa04-n02.pdf

3. MAS Guidelines to Notice 626, 30 June 2025 amendments  
   Use: guidance-vs-obligation distinction.  
   URL: https://www.mas.gov.sg/-/media/amld-amendments---30-june-2025/guidelines-to-mas-notice-626.pdf

4. ACRA Guidance on Register of Controllers for Companies, version 2, issued 16 June 2025  
   Use: beneficial ownership / KYC extraction.  
   URL: https://www.acra.gov.sg/regulations/practice-directions-registrars-interpretations-guidance/rorc-rond-rons-guidance/

5. DBS Annual Report 2025  
   Use: financial table extraction.  
   URL: https://www.dbs.com/annualreports/2025/i/pdf/dbs-ar-2025.pdf

6. OCBC Annual Report 2025  
   Use: financial statement and governance extraction.  
   URL: https://www.ocbc.com/iwov-resources/sg/ocbc/gbc/pdf/investors/annual-reports/2025/2025-annual-report-en.pdf

7. UOB Annual Report 2025  
   Use: financial table extraction from SGX-hosted PDF.  
   URL: https://links.sgx.com/1.0.0/corporate-announcements/CJ5LTSEV6VGWLF37/878788_UOB%20AR2025.pdf

8. NFIP Claims Manual, June 2025 edition  
   Use: insurance claims workflow extraction.  
   URL: https://agents.floodsmart.gov/sites/default/files/media/document/2025-08/fema_nfip-ClaimsManual-June2025-508c.pdf

9. SFIP Commentary, June 2025 update  
   Use: policy clause retrieval and coverage interpretation with commentary.  
   URL: https://agents.floodsmart.gov/sites/default/files/media/document/2025-08/June%202025%20NFIP_SFIP_Commentary%20%28508c%29.pdf

### Dataset use
Use these as optional benchmark datasets, not all in the live demo.

1. CUAD — Contract Understanding Atticus Dataset  
   Use: legal clause extraction and contract QA.  
   Scope: 510 commercial contracts, 13,000+ labels, 41 clause categories.  
   Source: https://zenodo.org/records/4595826  
   Recommended use: select 10 contracts and 5 clause types. Do not ingest all 510 initially.

2. FUNSD — Form Understanding in Noisy Scanned Documents  
   Use: noisy scanned form OCR/layout/key-value extraction.  
   Scope: 199 annotated forms, 31,485 words, 9,707 semantic entities, 5,304 relations.  
   Source: https://guillaumejaume.github.io/FUNSD/  
   Recommended use: select 20 forms from train/test for parser stress tests.

3. DocLayNet  
   Use: document layout benchmark only if time permits.  
   Scope: 80,863 pages with bounding boxes for 11 layout classes.  
   Source: https://github.com/DS4SD/DocLayNet and https://huggingface.co/datasets/docling-project/DocLayNet  
   Recommended use: do not train a layout model. Use a small sample to compare whether parser outputs preserve titles/tables/figures/lists.

4. FATURA — optional stretch  
   Use: invoice extraction.  
   Scope: 10,000 synthetic invoice images, 50 layouts.  
   Source: https://zenodo.org/records/8261508  
   Recommended use: optional invoice benchmark only.

## Benchmark methodology
The benchmark must prove the app is not hand-waved. It should be simple, reproducible, and honest.

### Benchmark files to commit before running tests
Commit these first:

```text
benchmark/
  questions.csv
  expected_sources.csv
  expected_answers.csv
  scoring_config.yaml
  README.md
scripts/
  run_benchmark.py
```

### Then run tests and commit results separately
Second commit:

```text
results/run_001/
  raw_outputs.jsonl
  retrieved_chunks.jsonl
  scores.csv
  parser_scores.csv
  summary.md
  run_config.yaml
  environment.txt
```

README statement:

> The benchmark set and scoring script were committed before the result run. Raw outputs, retrieved chunks, scores, and failures are included for inspection. Anyone can rerun the benchmark locally with `python scripts/run_benchmark.py --run-id run_001`.

### Benchmark categories

#### A. Parser benchmark
Question: Can the system turn messy documents into usable structured text?

Compare:
- PyMuPDF/pdfplumber baseline.
- Docling parser.
- OCR fallback if implemented.

Metrics:
- parse_success_rate = parsed_pages / total_pages
- empty_page_rate
- avg_latency_seconds_per_page
- table_preservation_score, manual 0–2
- reading_order_score, manual 0–2
- key_value_extraction_f1 for FUNSD sample
- crash_count

Manual table score:
- 0 = table lost/unusable
- 1 = table partially usable
- 2 = table structure mostly preserved

Manual reading order score:
- 0 = order badly broken
- 1 = understandable but flawed
- 2 = mostly correct

#### B. Retrieval benchmark
Question: Does the system retrieve the correct evidence?

Use `questions.csv` with expected document/page/evidence snippet.

Metrics:
- hit_at_1
- recall_at_3
- recall_at_5
- MRR
- citation_page_match_rate
- context_precision, optional Ragas/DeepEval
- context_recall, optional Ragas/DeepEval

Definitions:
- hit_at_1 = correct source appears as top chunk.
- recall_at_5 = correct source appears anywhere in top five chunks.
- MRR = reciprocal rank of first correct chunk.

#### C. Answer/citation benchmark
Question: Does the system answer correctly and stay grounded?

Metrics:
- answer_correctness, manual 0/0.5/1
- citation_support, manual 0/0.5/1
- faithfulness, optional LLM-as-judge
- unsupported_claim_count
- hallucination_flag
- abstention_correctness

Manual answer correctness:
- 1 = answer materially correct
- 0.5 = partially correct but incomplete
- 0 = wrong or unsupported

Manual citation support:
- 1 = cited source directly supports the claim
- 0.5 = related but incomplete support
- 0 = citation does not support claim

#### D. Report benchmark
Question: Does the generated report look compliance-ready and evidence-grounded?

Metrics:
- required_sections_present: yes/no
- evidence_table_present: yes/no
- unsupported_claim_count
- missing_info_section_present: yes/no
- risk_flags_grounded: manual 0/0.5/1
- professional_format_score: manual 0–2

## Benchmark questions schema
`benchmark/questions.csv`

Columns:
- question_id
- domain
- task_type
- question
- expected_document
- expected_page_start
- expected_page_end
- expected_answer_short
- expected_evidence_snippet
- should_abstain
- notes

Example:

```csv
question_id,domain,task_type,question,expected_document,expected_page_start,expected_page_end,expected_answer_short,expected_evidence_snippet,should_abstain,notes
Q001,finance_regulatory,retrieval_qa,"What are the key expectations around technology risk governance?",mas-trm-guidelines-2021.pdf,,,,"Financial institutions should establish sound technology risk governance with board/senior-management oversight.","technology risk governance",false,"Exact page filled after parsing."
Q002,kyc,extraction,"Who qualifies as a registrable controller under the ACRA guidance?",acra-registrable-controllers-guidance-2025.pdf,,,,"A controller is generally an individual/legal entity with significant interest or significant control, subject to guidance definitions.","significant interest",false,"Use ACRA source."
Q003,insurance,abstention,"Does the NFIP policy cover earthquake damage unrelated to flood?",sfip-commentary-2025.pdf,,,,"Insufficient evidence or answer should indicate flood policy scope/exclusions, not general earthquake cover.","direct physical loss by or from flood",false,"Tests narrow support."
```

## Report generation format
The report must resemble a real compliance-ready document. Use a sober, professional format.

### Report title
**Compliance Intelligence Review**

### Header metadata
- Report ID
- Prepared for: Demo / Public Work Trial
- Prepared by: EvidenceOS Mini
- Prepared date/time
- Document bundle name
- Documents reviewed
- Parser version
- Retrieval config
- LLM/model config
- Confidentiality label: Public demo data only
- Disclaimer: Not legal, financial, insurance, or regulatory advice

### Executive summary
Short, direct summary:
- What was reviewed
- Main findings
- Highest-risk gaps
- Whether evidence was sufficient

### Scope and limitations
Include:
- Documents included
- Documents excluded
- Known extraction limitations
- OCR/layout limitations
- Benchmark status
- No private/client data used

### Document inventory
Table:
| # | Document | Domain | Type | Pages | Parser | Status | SHA256 |

### Key findings
Each finding must be claim/evidence structured.

Format:

```text
Finding F-001 — Technology risk governance expectations identified
Status: Supported
Risk level: Medium
Claim: [one clear claim]
Evidence: [short quote/snippet]
Source: [filename], page [x], section [y]
Analyst note: [optional inference clearly marked]
```

### Extracted facts register
Table:
| Fact ID | Fact | Source | Page | Evidence quote | Confidence | Type |

Types:
- extracted_fact
- inferred_conclusion
- missing_information
- contradiction

### Risk flags
Table:
| Risk ID | Risk | Severity | Evidence | Source | Recommended next step |

Severity:
- Critical
- High
- Medium
- Low
- Informational

### Missing information
Table:
| Missing item | Why it matters | Required source | Impact |

### Contradictions and conflicts
Table:
| Conflict ID | Conflict | Source A | Source B | Resolution status |

If no contradictions:
> No contradictions were detected within the reviewed evidence. This does not mean the document bundle is complete.

### Evidence table
This is mandatory.

| Claim ID | Claim | Evidence quote | Source document | Page | Section | Support level | Confidence |

### Recommended next actions
Each action should be grounded:
| Action | Rationale | Evidence source | Owner |

### Appendix A — Retrieval log
Include top chunks retrieved for each user question/report section.

### Appendix B — Benchmark run summary
Include benchmark metrics and failure cases.

### Appendix C — Model and parser configuration
Include:
- parser versions
- chunk size
- chunk overlap
- embedding model
- vector DB
- retrieval top_k
- reranking setting
- LLM model
- generation temperature

## UI requirements

### Page 1: Document library
- Upload PDFs.
- Show parse status.
- Show parser used.
- Show page count.
- Show extraction errors.
- Show source URLs.
- Show SHA256 hash.

### Page 2: Evidence Q&A
- Question input.
- Answer block.
- Evidence cards with source/page/snippet.
- “Insufficient evidence” state.
- Toggle: show retrieved chunks.

### Page 3: Report builder
- Select report type:
  - KYC/beneficial ownership brief
  - Technology risk compliance brief
  - Insurance claims review
  - General compliance intelligence review
- Generate report.
- Export Markdown and PDF optional.

### Page 4: Benchmark dashboard
- Select run.
- Show parser metrics.
- Show retrieval metrics.
- Show answer/citation metrics.
- Show failures.
- Link raw outputs.

## Implementation phases

### Phase 0 — Repo scaffold
Deliverables:
- monorepo or simple repo structure
- Docker Compose with API + Qdrant
- README with setup
- `.env.example`
- pre-commit formatting optional

Commit message:
`chore: scaffold evidenceos mini repo`

### Phase 1 — Public document manifest and downloader
Deliverables:
- manifests/public_docs.csv
- scripts/download_public_docs.py
- data/raw_docs/.gitkeep
- README instructions

Commit message:
`data: add public document manifest and downloader`

### Phase 2 — Parser baseline
Deliverables:
- PyMuPDF/pdfplumber parser
- normalized `Document`, `Page`, `Chunk` JSONL output
- CLI: `python scripts/parse_docs.py --parser baseline`

Commit message:
`feat: add baseline PDF parsing pipeline`

### Phase 3 — Docling parser
Deliverables:
- Docling parser adapter
- markdown/json export
- table/section metadata when available
- parser comparison logs

Commit message:
`feat: add docling structured document parser`

### Phase 4 — Chunking and vector indexing
Deliverables:
- chunking pipeline
- embeddings
- Qdrant collection setup
- metadata filters
- CLI: `python scripts/index_docs.py`

Commit message:
`feat: index parsed chunks into qdrant`

### Phase 5 — Evidence retrieval and cited Q&A
Deliverables:
- `/search` endpoint
- `/qa` endpoint
- grounded answer schema
- abstention logic
- retrieved chunks stored per answer

Commit message:
`feat: add evidence-grounded QA with citations`

### Phase 6 — Audit-ready report generator
Deliverables:
- report schema
- Markdown report renderer
- professional compliance-ready template
- export `.md`; optional PDF export

Commit message:
`feat: generate audit-ready compliance review reports`

### Phase 7 — Benchmark definition commit
Important: commit benchmark before running.

Deliverables:
- benchmark/questions.csv
- benchmark/expected_answers.csv
- benchmark/expected_sources.csv
- benchmark/scoring_config.yaml
- scripts/run_benchmark.py

Commit message:
`test: add fixed benchmark set and scoring script`

### Phase 8 — Benchmark run commit
Deliverables:
- results/run_001/raw_outputs.jsonl
- results/run_001/retrieved_chunks.jsonl
- results/run_001/scores.csv
- results/run_001/summary.md
- results/run_001/environment.txt

Commit message:
`eval: add first reproducible benchmark run`

### Phase 9 — Frontend polish and demo script
Deliverables:
- clean UI
- sample report in `examples/`
- benchmark dashboard
- final README
- demo script

Commit message:
`docs: add demo guide and final work trial explanation`

## README structure
The final README should include:

1. One-line project description.
2. Why this was built for Akro.
3. Demo video link placeholder.
4. Architecture diagram.
5. Setup instructions.
6. How to download public docs.
7. How to parse/index docs.
8. How to ask cited questions.
9. How to generate report.
10. Benchmark reproducibility.
11. Results summary.
12. Known limitations.
13. What I would improve inside a real Akro internship.

## Non-negotiable success criteria
- The app runs locally.
- The system returns citations with filename and page.
- The system can abstain.
- The report includes an evidence table.
- Benchmark questions are committed before results.
- Raw outputs are included.
- Failures are visible, not hidden.

## Scope control
Do not build:
- user auth;
- multi-tenant permissions;
- production security;
- fine-tuning;
- huge dataset ingestion;
- complex agent framework;
- beautiful but fragile UI.

Build:
- a small, honest, reliable pipeline;
- a clear benchmark;
- a professional report;
- a strong README.

## Suggested 5-minute demo flow
1. Open README and architecture diagram.
2. Open app and show document library.
3. Upload or select preloaded public document bundle.
4. Show parse/chunk stats.
5. Ask: “Who qualifies as a registrable controller?”
6. Show answer + ACRA citation.
7. Ask a question that should abstain.
8. Generate “Compliance Intelligence Review.”
9. Show evidence table and missing information section.
10. Show benchmark dashboard and the two commits proving benchmark integrity.

## Final submission package
Submit to Akro:
- GitHub repo.
- Loom demo.
- `AKRO_BUILD_REFERENCE.md`.
- Generated sample report.
- Benchmark result summary.
- A short message explaining that the build is not production-grade but demonstrates learning speed, product understanding, and engineering judgment.
