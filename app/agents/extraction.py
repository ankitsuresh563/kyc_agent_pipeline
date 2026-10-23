"""Extraction agent: turns raw text into validated structured fields.

Uses an LLM when OPENAI_API_KEY is set, otherwise deterministic regex extraction.
Sensitive identifiers (Aadhaar, account numbers) are masked at extraction time.
"""
import re
from typing import Any, Dict

from app.llm import llm_available, llm_json
from app.schemas import ExtractedDoc

EXPECTED = {
    "id_proof": ["name", "dob", "pan"],
    "income_proof": ["name", "net_pay", "month"],
    "bank_statement": ["name", "avg_balance", "closing_balance"],
}


def _money(s: str) -> float:
    return float(re.sub(r"[^\d.]", "", s))


def _find(pattern: str, text: str, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _mask(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return "XXXX-XXXX-" + digits[-4:] if digits else value


def _regex_extract(doc_type: str, text: str) -> Dict[str, Any]:
    f: Dict[str, Any] = {}
    f["name"] = _find(r"(?:employee name|account holder|name)\s*:\s*([^\n]+)", text)
    if doc_type == "id_proof":
        f["dob"] = _find(r"date of birth\s*:\s*(\d{2}/\d{2}/\d{4})", text)
        f["pan"] = _find(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text, 0)
        aad = _find(r"aadhaar\s*:\s*([\d ]{12,14})", text)
        if aad:
            f["aadhaar_masked"] = _mask(aad)
    elif doc_type == "income_proof":
        v = _find(r"net pay\s*:\s*(?:INR|Rs\.?)?\s*([\d,\.]+)", text)
        f["net_pay"] = _money(v) if v else None
        f["month"] = _find(r"month\s*:\s*([^\n]+)", text)
        f["employer"] = _find(r"^([^\n]+?)\s*-\s*salary slip", text, re.I | re.M)
    elif doc_type == "bank_statement":
        a = _find(r"average monthly balance\s*:\s*(?:INR|Rs\.?)?\s*([\d,\.]+)", text)
        c = _find(r"closing balance\s*:\s*(?:INR|Rs\.?)?\s*([\d,\.]+)", text)
        f["avg_balance"] = _money(a) if a else None
        f["closing_balance"] = _money(c) if c else None
        acc = _find(r"account no\s*:\s*([\d ]+)", text)
        if acc:
            f["account_masked"] = _mask(acc)
    return f


def _llm_extract(doc_type: str, text: str) -> Dict[str, Any]:
    system = (
        "Extract fields from a banking document. Return JSON with keys: "
        + ", ".join(EXPECTED[doc_type])
        + ". Use null when a field is absent. Dates as DD/MM/YYYY, amounts as numbers."
    )
    return llm_json(system, text)


def extract(filename: str, doc_type: str, text: str) -> ExtractedDoc:
    if doc_type not in EXPECTED:
        return ExtractedDoc(filename=filename, doc_type=doc_type, fields={}, confidence=0.0)
    fields = _llm_extract(doc_type, text) if llm_available() else _regex_extract(doc_type, text)
    expected = EXPECTED[doc_type]
    found = sum(1 for k in expected if fields.get(k) not in (None, ""))
    return ExtractedDoc(
        filename=filename, doc_type=doc_type, fields=fields, confidence=round(found / len(expected), 2)
    )
