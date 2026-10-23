import os

import pytest

from app.orchestrator import run_case

ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "samples")


def load(case):
    folder = os.path.join(ROOT, case)
    return {f: open(os.path.join(folder, f), encoding="utf-8").read() for f in os.listdir(folder)}


def test_clean_case_is_approved_without_human():
    r = run_case("c1", load("case_001_clean"))
    assert r.decision == "APPROVE_RECOMMENDED" and not r.needs_human
    assert all(f.severity == "info" for f in r.compliance)


def test_mismatch_case_flags_name_income_and_balance():
    r = run_case("c2", load("case_002_mismatch"))
    msgs = " ".join(f.message for f in r.validation + r.compliance)
    assert "Name mismatch" in msgs and "below minimum" in msgs
    assert r.decision == "REJECT_RECOMMENDED" and r.needs_human


def test_incomplete_case_requests_documents():
    r = run_case("c3", load("case_003_incomplete"))
    assert r.decision == "REQUEST_DOCUMENTS"


def test_pii_is_masked_in_output():
    r = run_case("c1", load("case_001_clean"))
    dump = r.model_dump_json()
    assert "1234 5678 9012" not in dump and "123456789012" not in dump


def test_every_compliance_finding_cites_a_clause():
    r = run_case("c1", load("case_001_clean"))
    assert r.compliance and all(f.clause for f in r.compliance)
