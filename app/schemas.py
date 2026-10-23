from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ExtractedDoc(BaseModel):
    filename: str
    doc_type: str
    fields: Dict[str, Any]
    confidence: float


class Finding(BaseModel):
    severity: str  # info | warning | critical
    message: str
    clause: Optional[str] = None  # policy clause cited


class CaseResult(BaseModel):
    case_id: str
    documents: List[ExtractedDoc]
    validation: List[Finding]
    compliance: List[Finding]
    decision: str  # APPROVE_RECOMMENDED | REJECT_RECOMMENDED | REQUEST_DOCUMENTS | HUMAN_REVIEW
    confidence: float
    needs_human: bool
    audit: List[Dict[str, Any]]
