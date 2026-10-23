"""Validation agent: cross-document consistency and format checks."""
import re
from difflib import SequenceMatcher
from typing import List

from app.schemas import ExtractedDoc, Finding

REQUIRED = ["id_proof", "income_proof", "bank_statement"]
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def missing_documents(docs: List[ExtractedDoc]) -> List[str]:
    present = {d.doc_type for d in docs}
    return [r for r in REQUIRED if r not in present]


def validate(docs: List[ExtractedDoc]) -> List[Finding]:
    findings: List[Finding] = []

    for m in missing_documents(docs):
        findings.append(Finding(severity="critical", message=f"Missing required document: {m}", clause="P-6"))

    names = [(d.doc_type, _norm(d.fields["name"])) for d in docs if d.fields.get("name")]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ratio = SequenceMatcher(None, names[i][1], names[j][1]).ratio()
            if ratio < 0.85:
                findings.append(
                    Finding(
                        severity="critical",
                        message=f"Name mismatch between {names[i][0]} and {names[j][0]} (similarity {ratio:.2f})",
                        clause="P-5",
                    )
                )

    for d in docs:
        if d.doc_type == "id_proof":
            pan = d.fields.get("pan")
            if not pan or not PAN_RE.match(pan):
                findings.append(Finding(severity="critical", message="PAN missing or invalid format", clause="P-1"))
        if d.confidence < 0.67 and d.doc_type != "unknown":
            findings.append(
                Finding(severity="warning", message=f"Low extraction confidence on {d.filename} ({d.confidence})")
            )
        if d.doc_type == "unknown":
            findings.append(Finding(severity="warning", message=f"Could not classify {d.filename}"))
    return findings
