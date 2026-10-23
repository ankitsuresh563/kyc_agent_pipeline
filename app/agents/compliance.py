"""Compliance agent: retrieves relevant policy clauses (RAG) and applies them.

Thresholds are parsed from the retrieved clause text, so changing policy.md changes behaviour
and every finding cites the clause it came from.
"""
import os
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.schemas import ExtractedDoc, Finding

POLICY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policy", "policy.md")
STOP = {"the", "a", "of", "for", "at", "be", "is", "to", "and", "must", "every", "in", "than"}


def _tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP}


def load_policy() -> Dict[str, str]:
    clauses = {}
    with open(POLICY_PATH, encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                cid, text = [p.strip() for p in line.split("|", 1)]
                clauses[cid] = text
    return clauses


def retrieve(query: str, clauses: Dict[str, str]) -> Tuple[str, str]:
    q = _tokens(query)
    best = max(clauses.items(), key=lambda kv: len(q & _tokens(kv[1])))
    return best


def _doc(docs: List[ExtractedDoc], t: str) -> Optional[ExtractedDoc]:
    return next((d for d in docs if d.doc_type == t), None)


def _age(dob: str, today: Optional[date] = None) -> int:
    today = today or date.today()
    b = datetime.strptime(dob, "%d/%m/%Y").date()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def check(docs: List[ExtractedDoc]) -> List[Finding]:
    clauses = load_policy()
    out: List[Finding] = []

    idd, inc, bank = _doc(docs, "id_proof"), _doc(docs, "income_proof"), _doc(docs, "bank_statement")

    if idd and idd.fields.get("dob"):
        cid, text = retrieve("applicant age years minimum maximum", clauses)
        lo, hi = map(int, re.search(r"at least (\d+) years and at most (\d+)", text).groups())
        age = _age(idd.fields["dob"])
        if lo <= age <= hi:
            out.append(Finding(severity="info", message=f"Age {age} within allowed range {lo}-{hi}", clause=cid))
        else:
            out.append(Finding(severity="critical", message=f"Age {age} outside allowed range {lo}-{hi}", clause=cid))

    if inc and inc.fields.get("net_pay") is not None:
        cid, text = retrieve("net monthly income minimum eligibility", clauses)
        need = float(re.search(r"INR\s*([\d,]+)", text).group(1).replace(",", ""))
        have = inc.fields["net_pay"]
        sev, verb = ("info", "meets") if have >= need else ("critical", "is below")
        out.append(Finding(severity=sev, message=f"Net monthly income INR {have:,.0f} {verb} minimum INR {need:,.0f}", clause=cid))

    if bank and bank.fields.get("avg_balance") is not None:
        cid, text = retrieve("average monthly bank balance minimum", clauses)
        need = float(re.search(r"INR\s*([\d,]+)", text).group(1).replace(",", ""))
        have = bank.fields["avg_balance"]
        sev, verb = ("info", "meets") if have >= need else ("critical", "is below")
        out.append(Finding(severity=sev, message=f"Average balance INR {have:,.0f} {verb} minimum INR {need:,.0f}", clause=cid))

    return out
