# Multi-Agent KYC & Loan Document Processing Pipeline

A multi-agent system that classifies, extracts, validates and policy-checks loan/KYC documents,
then routes the case to auto-recommendation or a human reviewer. Every decision is audit-logged
and every compliance finding cites the policy clause it came from.

## Architecture

```
documents -> [Intake] -> [Extraction] -> [Validation] -> [Compliance (RAG over policy)] -> [Router]
              classify    structured       cross-doc       thresholds parsed from           APPROVE_RECOMMENDED
              + OCR       fields + conf.   consistency     retrieved clauses + cites        REJECT_RECOMMENDED
                                                                                            REQUEST_DOCUMENTS
                                                                                            HUMAN_REVIEW
```

| Agent | File | Responsibility |
|---|---|---|
| Intake | `app/agents/intake.py` | Read txt/pdf/image (optional OCR), classify document type |
| Extraction | `app/agents/extraction.py` | Regex by default, LLM when `OPENAI_API_KEY` set; masks Aadhaar/account numbers |
| Validation | `app/agents/validation.py` | Missing docs, PAN format, cross-document name matching |
| Compliance | `app/agents/compliance.py` | Retrieves clauses from `policy/policy.md`, parses thresholds, cites clause IDs |
| Router | `app/orchestrator.py` | Confidence-based routing; a human always confirms rejections |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_demo.py            # runs 3 sample cases (add --audit for the trail)
pytest -q                     # tests
uvicorn app.main:app --reload # API docs at http://localhost:8000/docs
```

Docker: `docker build -t kyc-agents . && docker run -p 8000:8000 kyc-agents`

API: `POST /cases` (multipart files) -> result; `GET /reviews` -> human queue; `POST /reviews/{id}` -> reviewer decision.

## Upgrade paths (good interview talking points)
- Wrap each agent as a **LangGraph** node (functions already take/return plain data).
- Set `OPENAI_API_KEY` (or point `app/llm.py` at Azure OpenAI / a local Llama) for LLM extraction.
- Replace token-overlap retrieval in `compliance.retrieve` with embeddings + pgvector/FAISS.
- Add `pdfplumber` / `pytesseract` for real PDFs and scanned images (already wired in `intake.read_document`).
- Persist cases/reviews in PostgreSQL and add authentication.

## Design decisions
- **Human-in-the-loop by design:** rejections are never automatic; low confidence or warnings go to review.
- **Explainability:** each finding carries a clause ID; audit trail records every agent step.
- **Data protection:** identifiers are masked before leaving the extraction step.
- **Deterministic fallback:** system is testable without any LLM or network.

## Resume bullets (fill in your own measured numbers)
- Built a multi-agent KYC/loan document pipeline (intake, extraction, validation, policy-grounded compliance) with confidence-based human-review routing and full audit logging.
- Implemented clause-cited compliance checks where eligibility thresholds are parsed from retrieved policy text, so policy changes need no code changes.
- Delivered as a FastAPI service with Docker and a pytest suite covering approve / reject / missing-document / PII-masking scenarios.
