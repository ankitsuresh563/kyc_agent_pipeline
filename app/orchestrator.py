"""Orchestrator: runs the agents in order, records an audit trail, and routes to a human when needed.

The graph is intentionally small and explicit (intake -> extraction -> validation -> compliance -> router).
Each step is a plain function so it can be wrapped as a LangGraph node with no changes.
"""
import time
from typing import Dict, List

from app.agents import compliance, extraction, intake, validation
from app.schemas import CaseResult, ExtractedDoc

AUTO_CONFIDENCE = 0.85


def run_case(case_id: str, documents: Dict[str, str]) -> CaseResult:
    audit: List[dict] = []

    def log(agent: str, detail: str):
        audit.append({"ts": round(time.time(), 3), "agent": agent, "detail": detail})

    docs: List[ExtractedDoc] = []
    for fname, text in documents.items():
        dtype = intake.classify(text)
        log("intake", f"{fname} classified as {dtype}")
        d = extraction.extract(fname, dtype, text)
        log("extraction", f"{fname}: confidence {d.confidence}")
        docs.append(d)

    val = validation.validate(docs)
    log("validation", f"{len(val)} findings")
    comp = compliance.check(docs)
    log("compliance", f"{len(comp)} findings, clauses cited: {sorted({f.clause for f in comp if f.clause})}")

    known = [d.confidence for d in docs if d.doc_type != "unknown"]
    confidence = round(sum(known) / len(known), 2) if known else 0.0
    critical = [f for f in val + comp if f.severity == "critical"]
    warnings = [f for f in val + comp if f.severity == "warning"]

    if validation.missing_documents(docs):
        decision, needs_human = "REQUEST_DOCUMENTS", True
    elif confidence < AUTO_CONFIDENCE or warnings:
        decision, needs_human = "HUMAN_REVIEW", True
    elif critical:
        decision, needs_human = "REJECT_RECOMMENDED", True  # a human always confirms a rejection
    else:
        decision, needs_human = "APPROVE_RECOMMENDED", False
    log("router", f"decision={decision} needs_human={needs_human}")

    return CaseResult(
        case_id=case_id, documents=docs, validation=val, compliance=comp,
        decision=decision, confidence=confidence, needs_human=needs_human, audit=audit,
    )
