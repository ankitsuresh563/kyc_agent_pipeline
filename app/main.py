"""FastAPI service. Run: uvicorn app.main:app --reload"""
import uuid
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.orchestrator import run_case
from app.schemas import CaseResult

app = FastAPI(title="KYC & Loan Document Agent Pipeline")
CASES: Dict[str, CaseResult] = {}
REVIEW_LOG: List[dict] = []


class ReviewDecision(BaseModel):
    reviewer: str
    decision: str  # APPROVE | REJECT
    note: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/cases", response_model=CaseResult)
async def create_case(files: List[UploadFile] = File(...)):
    docs = {f.filename: (await f.read()).decode("utf-8", errors="ignore") for f in files}
    case_id = uuid.uuid4().hex[:8]
    CASES[case_id] = run_case(case_id, docs)
    return CASES[case_id]


@app.get("/reviews")
def review_queue():
    return [c for c in CASES.values() if c.needs_human and c.case_id not in {r["case_id"] for r in REVIEW_LOG}]


@app.post("/reviews/{case_id}")
def submit_review(case_id: str, body: ReviewDecision):
    if case_id not in CASES:
        raise HTTPException(404, "case not found")
    entry = {"case_id": case_id, **body.model_dump()}
    REVIEW_LOG.append(entry)
    return entry
