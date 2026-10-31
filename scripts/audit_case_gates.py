"""Case admission gates: a task is only usable if an empty run scores zero and the
reference answer scores full marks.

    python -X utf8 scripts/audit_case_gates.py            # recompute and print
    python -X utf8 scripts/audit_case_gates.py --check    # compare with the frozen file

No product is started. The empty arm is a fresh temporary directory; the
reference arm is the published synthetic answer for that case, which is built
from the frozen oracle and is never treated as a product run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation_v3 import grader  # noqa: E402

CASES = ("T01", "T02", "T03", "T04", "T05")
GOLDEN = {"T01": "G1", "T02": "G2", "T03": "G3", "T04": "G4", "T05": "G5"}
OUT = ROOT / "reports/week3/case-gates.json"


def row(case, label, outputs, shown):
    result = grader.adjudicate(case, outputs)
    legacy = result["legacy_artifact_result"]
    weight = legacy.get("all_weight")
    maximum = round(weight * 0.6, 6) if weight else 60.0
    return {
        "case_id": case,
        "arm": label,
        "outputs": shown,
        "objective_score": legacy.get("objective_score"),
        "objective_max": maximum,
        "all_checks_passed": legacy.get("all_checks_passed"),
        "guards_passed": all(guard["passed"] for guard in result["validity_guards"]),
        "accepted": result["accepted"],
    }


def build():
    rows = []
    for case in CASES:
        empty = Path(tempfile.mkdtemp(prefix=f"noop-{case}-"))
        try:
            rows.append(row(case, "no_op_empty_outputs", empty, "<empty temporary directory>"))
        finally:
            for leftover in sorted(empty.rglob("*"), reverse=True):
                leftover.unlink() if leftover.is_file() else leftover.rmdir()
            empty.rmdir()
        golden = ROOT / "public/grader-audit-v3" / GOLDEN[case] / "outputs"
        rows.append(row(case, "reference_answer", golden, f"public/grader-audit-v3/{GOLDEN[case]}/outputs"))
    verdict = {
        "schema": "tx-harness/case-admission-gates/v1",
        "rule": "an empty run must score 0 and the reference answer must reach full marks; "
                "otherwise the case is not admissible for scoring",
        "cases": rows,
        "counts": {
            "cases": len(CASES),
            "no_op_zero": sum(1 for item in rows
                              if item["arm"] == "no_op_empty_outputs"
                              and item["objective_score"] == 0),
            "reference_full": sum(1 for item in rows
                                  if item["arm"] == "reference_answer"
                                  and item["objective_score"] == item["objective_max"]),
        },
        "limits": "Artifact-level admission only. It shows the task cannot be passed with no "
                  "work and can be passed with the frozen answer; it says nothing about a "
                  "product's behaviour.",
    }
    verdict["passed"] = (verdict["counts"]["no_op_zero"] == len(CASES)
                         and verdict["counts"]["reference_full"] == len(CASES))
    return verdict


def write(value):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = build()
    if args.check:
        if not OUT.exists():
            print("FAIL missing " + str(OUT))
            return 1
        stored = json.loads(OUT.read_text(encoding="utf-8"))
        if stored != fresh:
            print("FAIL case-gate file drifted from a fresh recomputation")
            return 1
        print(json.dumps({"case_gates": "unchanged", "counts": fresh["counts"]}, ensure_ascii=False))
        return 0
    write(fresh)
    print(json.dumps({"counts": fresh["counts"], "passed": fresh["passed"]}, ensure_ascii=False))
    return 0 if fresh["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
