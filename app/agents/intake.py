"""Intake agent: reads a document (txt/pdf/image) and classifies its type."""
import os
import re

DOC_PATTERNS = {
    "id_proof": [r"permanent account number", r"\baadhaar\b", r"\bpan\s*:"],
    "income_proof": [r"salary slip", r"net pay", r"payslip"],
    "bank_statement": [r"account statement", r"closing balance", r"average monthly balance"],
}


def read_document(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        import pdfplumber  # optional dependency

        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    if ext in {".png", ".jpg", ".jpeg"}:
        import pytesseract  # optional dependency
        from PIL import Image

        return pytesseract.image_to_string(Image.open(path))
    with open(path, encoding="utf-8") as f:
        return f.read()


def classify(text: str) -> str:
    lowered = text.lower()
    scores = {
        t: sum(1 for p in pats if re.search(p, lowered)) for t, pats in DOC_PATTERNS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"
