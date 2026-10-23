"""Process every sample case and print a summary. Usage: python run_demo.py [--audit]"""
import os
import sys

from app.orchestrator import run_case

ROOT = os.path.join(os.path.dirname(__file__), "data", "samples")

for case in sorted(os.listdir(ROOT)):
    folder = os.path.join(ROOT, case)
    docs = {f: open(os.path.join(folder, f), encoding="utf-8").read() for f in sorted(os.listdir(folder))}
    r = run_case(case, docs)
    print(f"\n=== {case} -> {r.decision} (confidence {r.confidence}, human={r.needs_human})")
    for f in r.validation + r.compliance:
        print(f"  [{f.severity:8}] {f.message}" + (f"  ({f.clause})" if f.clause else ""))
    if "--audit" in sys.argv:
        for a in r.audit:
            print("   audit:", a)
