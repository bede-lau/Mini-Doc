# Coding Agent Prompt

You are my autonomous coding agent. Build a high-agency technical work sample for an internship application to Akro AI.

## Context
Akro builds sovereign/on-premise document intelligence for regulated industries. Public materials describe Akro as turning documents, records, and institutional knowledge into automated workflows with precision, privacy, explainability, source provenance, and agentic knowledge layers. Their finance/insurance/defence examples emphasize ingesting heterogeneous documents, preserving structure, grounding extracted data to exact sources, answering questions with citations, and generating defensible reports.

I need a serious but small technical demo, not a generic chat-with-PDF wrapper.

## Project name
**EvidenceOS Mini: Audit-Ready Document Intelligence for Regulated Workflows**

## Core goal
Build a local web app that:
1. ingests public/synthetic regulated PDFs;
2. parses them with a baseline parser and a Docling parser;
3. chunks and indexes text/tables with metadata;
4. answers questions using RAG with exact citations;
5. abstains when evidence is insufficient;
6. generates a professional compliance-ready report;
7. runs a reproducible benchmark where the benchmark questions are committed before the benchmark results.

## Tech stack
Use:
- Python 3.11+
- FastAPI backend
- Next.js + TypeScript frontend if feasible; otherwise Streamlit fallback
- Qdrant vector DB in Docker
- SentenceTransformers local embeddings by default
- PyMuPDF or pdfplumber for baseline parsing
- Docling for structured parsing
- Pydantic schemas
- Markdown report generation
- Optional: Ragas or DeepEval for LLM-as-judge metrics, but deterministic/manual metrics must work without them

Create clean, inspectable code. Prioritize reliability over visual polish.

## Required repo structure
Create this structure:

```text
.
  README.md
  docker-compose.yml
  .env.example
  apps/
    web/
  services/
    api/
      main.py
      routes/
      requirements.txt
  packages/
    core/
      parsers/
      chunking/
      retrieval/
      generation/
      reporting/
      evaluation/
      schemas/
      utils/
  scripts/
    download_public_docs.py
    parse_docs.py
    index_docs.py
    run_benchmark.py
  manifests/
    public_docs.csv
  benchmark/
    README.md
    questions.csv
    expected_answers.csv
    expected_sources.csv
    scoring_config.yaml
  data/
    raw_docs/.gitkeep
    parsed/.gitkeep
    chunks/.gitkeep
  results/.gitkeep
  examples/
    sample_compliance_report.md
```

If using a simpler structure is necessary, keep the same logical folders.

## Public document manifest
Create `manifests/public_docs.csv` with these columns:

```csv
filename,domain,document_type,source_url,why_use_it,recommended_demo_questions
```

Include these documents:

1. `mas-trm-guidelines-2021.pdf`  
URL: `https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulatory-and-Supervisory-Framework/Risk-Management/TRM-Guidelines-18-January-2021.pdf`  
Use: technology risk governance/control mapping.

2. `mas-notice-sfa04-n02-2025.pdf`  
URL: `https://www.mas.gov.sg/-/media/amld-amendments---30-june-2025/mas-notice-sfa04-n02.pdf`  
Use: AML/CFT obligation extraction.

3. `guidelines-to-mas-notice-626-2025.pdf`  
URL: `https://www.mas.gov.sg/-/media/amld-amendments---30-june-2025/guidelines-to-mas-notice-626.pdf`  
Use: guidance-vs-obligation distinction.

4. `acra-registrable-controllers-guidance-2025.pdf`  
URL page: `https://www.acra.gov.sg/regulations/practice-directions-registrars-interpretations-guidance/rorc-rond-rons-guidance/`  
Use: beneficial ownership/KYC extraction. Download the “Guidance on Register of Controllers for Companies” PDF version 2, issued 16 Jun 2025.

5. `dbs-annual-report-2025.pdf`  
URL: `https://www.dbs.com/annualreports/2025/i/pdf/dbs-ar-2025.pdf`  
Use: financial table extraction.

6. `ocbc-annual-report-2025.pdf`  
URL: `https://www.ocbc.com/iwov-resources/sg/ocbc/gbc/pdf/investors/annual-reports/2025/2025-annual-report-en.pdf`  
Use: financial statement/governance extraction.

7. `uob-annual-report-2025.pdf`  
URL: `https://links.sgx.com/1.0.0/corporate-announcements/CJ5LTSEV6VGWLF37/878788_UOB%20AR2025.pdf`  
Use: financial table extraction.

8. `nfip-claims-manual-june-2025.pdf`  
URL: `https://agents.floodsmart.gov/sites/default/files/media/document/2025-08/fema_nfip-ClaimsManual-June2025-508c.pdf`  
Use: insurance claims workflow extraction.

9. `sfip-commentary-june-2025.pdf`  
URL: `https://agents.floodsmart.gov/sites/default/files/media/document/2025-08/June%202025%20NFIP_SFIP_Commentary%20%28508c%29.pdf`  
Use: policy clause retrieval and insurance coverage interpretation.

## Dataset instructions
Do not ingest everything immediately. Add dataset source instructions in `README.md`.

Use these optional datasets:

1. CUAD: https://zenodo.org/records/4595826  
Use for legal contract clause extraction. Select 10 contracts and 5 clause types only.

2. FUNSD: https://guillaumejaume.github.io/FUNSD/  
Use for scanned forms/key-value extraction. Select 20 forms only.

3. DocLayNet: https://github.com/DS4SD/DocLayNet and https://huggingface.co/datasets/docling-project/DocLayNet  
Use only as a small layout/parser stress sample if time permits.

4. FATURA optional: https://zenodo.org/records/8261508  
Use only if invoice extraction is added as a stretch feature.

## Backend requirements
Build FastAPI endpoints:

### `POST /ingest`
Input: uploaded PDFs or references to files in `data/raw_docs`.
Output:
```json
{
  "document_id": "...",
  "filename": "...",
  "page_count": 0,
  "parser": "baseline|docling",
  "status": "success|failed",
  "sha256": "...",
  "errors": []
}
```

### `GET /documents`
List documents with parse status, page count, parser, source URL, SHA256.

### `POST /parse`
Run parser on selected docs. Support `parser=baseline` and `parser=docling`.

### `POST /index`
Index chunks into Qdrant.

### `POST /search`
Input: query, top_k, optional metadata filters.
Output: ranked evidence chunks with filename, page, section, snippet, score.

### `POST /qa`
Input: question.
Output:
```json
{
  "question": "...",
  "answer_type": "supported|insufficient_evidence|conflicting_evidence",
  "answer": "...",
  "claims": [],
  "citations": [],
  "retrieved_chunks": []
}
```

Rules:
- If no retrieved chunks pass threshold, return `insufficient_evidence`.
- Every material claim must have at least one citation.
- Include filename and page for each citation.

### `POST /reports/generate`
Input: report type and selected documents.
Output: Markdown report path and report JSON.

### `POST /benchmarks/run`
Run benchmark from `benchmark/questions.csv` and save to `results/run_001/`.

### `GET /benchmarks/results`
List runs and summary scores.

## Frontend requirements
Create four pages:

1. **Document Library**
   - Upload/select docs.
   - Show filename, domain, parser, status, pages, SHA256.

2. **Evidence Q&A**
   - Question box.
   - Answer output.
   - Citation cards.
   - Toggle to show raw retrieved chunks.
   - Clear `Insufficient evidence` state.

3. **Report Builder**
   - Choose report type:
     - KYC/Beneficial Ownership Brief
     - Technology Risk Compliance Brief
     - Insurance Claims Review
     - General Compliance Intelligence Review
   - Generate Markdown report.
   - Show evidence table.

4. **Benchmark Dashboard**
   - Show parser, retrieval, answer, citation, and report metrics.
   - Show failures clearly.
   - Link raw output files.

## Parsing requirements
Implement parser adapters with a common output schema:

```python
class ParsedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_start: int
    page_end: int
    section_heading: str | None
    chunk_text: str
    chunk_type: Literal["paragraph", "table", "list", "figure_caption", "ocr", "unknown"]
    bbox: list[float] | None = None
    parser: Literal["baseline", "docling", "ocr"]
    ocr: bool = False
    token_count: int
    source_url: str | None = None
```

Chunking rules:
- Preserve page metadata.
- Preserve section heading when available.
- Preserve table chunks separately when possible.
- Use chunk size around 500–900 tokens with overlap 80–150 tokens.
- Never combine chunks across documents.

## Retrieval requirements
- Store vectors in Qdrant.
- Store metadata: filename, document_type, domain, page_start, page_end, section, parser, chunk_type.
- Use dense retrieval first.
- Optional: add keyword/BM25 reranking later.
- Return top_k chunks with scores.

## QA generation requirements
The system prompt for answer generation must enforce:

```text
You are an evidence-grounded compliance analyst. Answer only using retrieved evidence. Every material claim must cite source filename and page. If the evidence is insufficient, say "Insufficient evidence in the reviewed documents." Separate facts from inferences. Do not invent regulations, numbers, obligations, or policy terms. If sources conflict, flag the conflict.
```

Output structured JSON, not free-form only.

## Audit-ready report format
Generate professional Markdown reports using this structure:

```markdown
# Compliance Intelligence Review

**Report ID:** CIR-[timestamp]  
**Prepared for:** Akro Work Trial Demo  
**Prepared by:** EvidenceOS Mini  
**Prepared date:** [datetime + timezone]  
**Document bundle:** [bundle name]  
**Confidentiality:** Public demo data only  
**Disclaimer:** This is a technical work sample using public/synthetic documents. It is not legal, financial, insurance, or regulatory advice.

## 1. Executive Summary
- Documents reviewed:
- Primary findings:
- Highest-risk gaps:
- Evidence sufficiency:

## 2. Scope and Limitations
- Included documents:
- Excluded documents:
- Known extraction limitations:
- Known retrieval limitations:
- No private/client data used.

## 3. Document Inventory
| # | Document | Domain | Type | Pages | Parser | Status | SHA256 |

## 4. Key Findings
### Finding F-001 — [Title]
**Status:** Supported / Partial / Insufficient Evidence / Conflicting Evidence  
**Risk level:** Critical / High / Medium / Low / Informational  
**Claim:** ...  
**Evidence:** “...”  
**Source:** filename.pdf, page X, section Y  
**Analyst note:** ...

## 5. Extracted Facts Register
| Fact ID | Fact | Type | Source | Page | Evidence quote | Confidence |

## 6. Risk Flags
| Risk ID | Risk | Severity | Evidence | Source | Recommended next step |

## 7. Missing Information
| Missing item | Why it matters | Required source | Impact |

## 8. Contradictions and Conflicts
| Conflict ID | Conflict | Source A | Source B | Resolution status |

## 9. Evidence Table
| Claim ID | Claim | Evidence quote | Source document | Page | Section | Support level | Confidence |

## 10. Recommended Next Actions
| Action | Rationale | Evidence source | Owner |

## Appendix A — Retrieval Log
Include top retrieved chunks for each question/report section.

## Appendix B — Benchmark Run Summary
Include metrics and top failure cases.

## Appendix C — Model and Parser Configuration
Include parser, chunk size, embedding model, vector DB, retrieval top_k, reranker, LLM, temperature.
```

The Evidence Table is mandatory.

## Benchmark requirements
Implement benchmark in phases.

### Phase commit rule
Commit 1 must include:
```text
benchmark/questions.csv
benchmark/expected_answers.csv
benchmark/expected_sources.csv
benchmark/scoring_config.yaml
scripts/run_benchmark.py
```

Commit 2 must include:
```text
results/run_001/raw_outputs.jsonl
results/run_001/retrieved_chunks.jsonl
results/run_001/scores.csv
results/run_001/summary.md
results/run_001/environment.txt
```

Do not modify benchmark questions after seeing results unless creating a new benchmark version like `benchmark_v2`.

### `questions.csv` schema
```csv
question_id,domain,task_type,question,expected_document,expected_page_start,expected_page_end,expected_answer_short,expected_evidence_snippet,should_abstain,notes
```

Seed at least 30 questions:
- 8 finance/regulatory questions
- 6 KYC/beneficial ownership questions
- 6 insurance claims/policy questions
- 5 financial table extraction questions
- 5 abstention/adversarial questions

### Metrics to implement locally
Parser metrics:
- parse_success_rate
- empty_page_rate
- avg_latency_seconds_per_page
- crash_count
- manual_table_score if manually filled
- manual_reading_order_score if manually filled

Retrieval metrics:
- hit_at_1
- recall_at_3
- recall_at_5
- MRR
- citation_page_match_rate

Answer/citation metrics:
- manual_answer_correctness 0/0.5/1
- manual_citation_support 0/0.5/1
- unsupported_claim_count
- abstention_correctness

Optional LLM-as-judge:
- faithfulness
- contextual relevancy
- answer relevancy

Important: Always save raw outputs and failures.

## Demo benchmark proof
In README include:

```text
Benchmark integrity: The benchmark questions, expected answers, expected sources, and scoring script were committed before running the test. Results were committed separately. Raw retrieved chunks and raw model outputs are included so the run can be inspected or rerun locally.
```

## README requirements
Write the README as if Marcus/Brian are scanning it quickly.

Include:
1. What this is.
2. Why it maps to Akro.
3. Demo video placeholder.
4. Architecture diagram.
5. Quickstart.
6. Download docs.
7. Parse/index docs.
8. Run app.
9. Generate report.
10. Run benchmark.
11. Benchmark integrity explanation.
12. Result summary.
13. Failure analysis.
14. Limitations.
15. What I would improve during an Akro internship.

## Commands that should work
Aim for:

```bash
cp .env.example .env
docker compose up -d qdrant
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
python scripts/download_public_docs.py
python scripts/parse_docs.py --parser baseline
python scripts/parse_docs.py --parser docling
python scripts/index_docs.py --parser docling
uvicorn services.api.main:app --reload
python scripts/run_benchmark.py --run-id run_001
```

If frontend is Next.js:

```bash
cd apps/web
npm install
npm run dev
```

## Quality bar
This project is successful if:
- It runs locally.
- It has public document sources.
- It parses at least 6 PDFs.
- It indexes chunks.
- It answers with citations.
- It abstains when evidence is weak.
- It generates a professional compliance-style report.
- It has a reproducible benchmark with committed questions and raw outputs.
- It shows failures honestly.

Do not waste time on:
- login/auth;
- multi-user permissions;
- production deployment;
- payment/billing;
- complex agent frameworks;
- fine-tuning;
- massive dataset ingestion.

Focus on showing engineering judgment, not completeness.

## Final deliverables
When done, produce:
- working repo;
- README;
- sample generated report in `examples/sample_compliance_report.md`;
- benchmark results in `results/run_001/summary.md`;
- demo script in `examples/demo_script.md`;
- a short final technical memo explaining what worked, what failed, and what would be improved next.
