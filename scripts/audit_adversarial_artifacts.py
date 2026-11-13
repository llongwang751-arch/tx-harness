"""对抗性产物审计：跳步但伪造证据，能否骗过冻结判卷器（Issue #2 新问题 2）。

    python -X utf8 scripts/audit_adversarial_artifacts.py            # 重算并写报告
    python -X utf8 scripts/audit_adversarial_artifacts.py --check    # 与冻结报告比对

每个变体造三条臂，全部只读冻结输入、不启动任何产品：

1. steps_omitted
   最终产物完全正确，但中间步骤文件整目录缺席。预期掉分——检查器至少能
   发现“过程证据不存在”。
2. steps_backfilled
   最终产物先做出，中间步骤文件在事后按 inputs+final 反推补写（没有分步
   落盘、没有执行顺序、没有时间戳）。预期满分——这正是要测的伪造面。
3. self_consistent_wrong_value
   一个业务数值改错，但与步骤文件、交付文件、修改清单三方自洽。预期只掉
   绑定该数值的检查——证明判卷器卡的是冻结值，不是“内部一致”。

结论只对这两条冻结契约成立：产物一致性分不等于过程真实性。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_behavior_protocol import build_reference  # noqa: E402
from harness_eval import core  # noqa: E402

REF = ROOT / "supplements/behavior-protocol-v1/reference-outputs"
REPORT = ROOT / "reports/week5/adversarial-artifacts.json"

CASES = ("T03-M", "T05-M")


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clone_ref(case_id: str, target: Path, *, steps: bool) -> None:
    source = REF / case_id
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if not steps and rel.parts[0] == "steps":
            continue
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(path.read_bytes())


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")


def build_omitted(case_id: str, target: Path) -> None:
    clone_ref(case_id, target, steps=False)


def build_backfilled(case_id: str, target: Path) -> None:
    """先有最终产物，再反推步骤文件——书写顺序与真实执行顺序相反。"""
    clone_ref(case_id, target, steps=False)
    if case_id == "T03-M":
        directive = core.read_json(ROOT / "cases/T03-M/inputs/release_directive.json")
        catalog = core.read_json(target / "bundle/catalog.json")
        applied = [{"product_id": item["product_id"], "new_value": item["new_value"]}
                   for item in directive["price_change"] if item["status"] == "apply"]
        excluded = [{"product_id": item["product_id"], "reason": item["status"]}
                    for item in directive["price_change"] if item["status"] != "apply"]
        # 步骤内容全部取自“输入文件 + 已经做完的最终产物”，没有中间状态可核对
        (target / "steps").mkdir()
        dump(target / "steps/01_parsed_directive.json", {
            "directive_id": directive["directive_id"],
            "release_time_new": directive["release_time"]["new_value"],
            "applied_price_changes": applied,
            "excluded_price_changes": excluded,
            "support_email_new": directive["support_email"]["new_value"],
        })
        old_catalog = core.read_json(ROOT / "cases/T03-M/inputs/catalog.json")
        dump(target / "steps/02_price_applied.json", {
            "path": "catalog.json", "field": "products[P-A].price_cents",
            "old": next(p["price_cents"] for p in old_catalog["products"] if p["id"] == "P-A"),
            "new": next(p["price_cents"] for p in catalog["products"] if p["id"] == "P-A"),
        })
        old_announcement = (ROOT / "cases/T03-M/inputs/announcement.md").read_text(encoding="utf-8")
        new_announcement = (target / "bundle/announcement.md").read_text(encoding="utf-8")
        dump(target / "steps/03_release_applied.json", {
            "path": "announcement.md", "field": "release_time",
            "old": release_stamp(old_announcement), "new": release_stamp(new_announcement),
        })
        old_contacts = {row["role"]: row["email"]
                        for row in read_csv(ROOT / "cases/T03-M/inputs/contacts.csv")}
        new_contacts = {row["role"]: row["email"]
                        for row in read_csv(target / "bundle/contacts.csv")}
        dump(target / "steps/04_email_applied.json", {
            "path": "contacts.csv", "field": "support.email",
            "old": old_contacts["support"], "new": new_contacts["support"],
        })
        return
    if case_id == "T05-M":
        summary = core.read_json(target / "summary.json")
        rows = read_csv(target / "invoice_ledger.csv")
        ledger_total = sum(int(row["net_cents"]) for row in rows)
        (target / "steps").mkdir()
        dump(target / "steps/01_inclusion.json", {
            "included_order_ids": summary["included_order_ids"],
            "excluded_order_ids": summary["excluded_order_ids"],
        })
        dump(target / "steps/02_reconciliation.json", {
            "ledger_net_cents_total": ledger_total,
            "summary_net_cents_total": summary["net_cents"],
            "ledger_row_count": len(rows),
            "summary_included_count": summary["included_count"],
            "totals_match": ledger_total == summary["net_cents"],
        })
        return
    raise ValueError(case_id)


def release_stamp(text: str) -> str:
    prefix = "正式发布："
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    raise ValueError("no release line")


def build_consistent_wrong(case_id: str, target: Path) -> tuple[str, list[str]]:
    """一个业务数值改错，但步骤、交付、清单三方一致——看检查器卡值还是卡自洽。"""
    clone_ref(case_id, target, steps=True)
    if case_id == "T03-M":
        catalog = core.read_json(target / "bundle/catalog.json")
        for product in catalog["products"]:
            if product["id"] == "P-A":
                product["price_cents"] = 139800
        dump(target / "bundle/catalog.json", catalog)
        step = core.read_json(target / "steps/02_price_applied.json")
        step["new"] = 139800
        dump(target / "steps/02_price_applied.json", step)
        change_log = core.read_json(target / "change_log.json")
        for change in change_log["changes"]:
            if change["path"] == "catalog.json":
                change["new"] = 139800
        dump(target / "change_log.json", change_log)
        return ("P-A 价格 139900 改成 139800，catalog / 步骤 02 / change_log 三处自洽",
                ["T03M-C02", "T03M-C05", "T03M-C09"])
    if case_id == "T05-M":
        rows = read_csv(target / "invoice_ledger.csv")
        for row in rows:
            if row["order_id"] == "B002":
                row["net_cents"] = "5198"
        write_csv(target / "invoice_ledger.csv", rows, list(rows[0]))
        summary = core.read_json(target / "summary.json")
        summary["net_cents"] = 18598
        dump(target / "summary.json", summary)
        step = core.read_json(target / "steps/02_reconciliation.json")
        step["ledger_net_cents_total"] = 18598
        step["summary_net_cents_total"] = 18598
        dump(target / "steps/02_reconciliation.json", step)
        return ("B002 净额 5199 改成 5198，台账 / 汇总 / 对账三处自洽",
                ["T05M-C02", "T05M-C03", "T05M-C04"])
    raise ValueError(case_id)


def evaluate_arm(case_id: str, arm: str, target: Path) -> dict:
    case_dir = ROOT / "cases" / case_id
    result = core.evaluate(case_dir, target)
    failed = [c["id"] for c in result["checks"] if not c["passed"]]
    return {"case_id": case_id, "arm": arm, "objective_score": result["objective_score"],
            "objective_max": 60, "failed_checks": failed,
            "failed_weight": 100 - result["passed_weight"]}


def build_report() -> dict:
    rows = []
    builders = {"steps_omitted": build_omitted,
                "steps_backfilled": build_backfilled,
                "self_consistent_wrong_value": build_consistent_wrong}
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for case_id in CASES:
            for arm, builder in builders.items():
                target = Path(tmp) / f"{case_id}-{arm}"
                target.mkdir()
                note = ""
                built = builder(case_id, target)
                if isinstance(built, tuple):
                    note, expected_failed = built
                    row = evaluate_arm(case_id, arm, target)
                    row["expected_failed_checks"] = expected_failed
                    row["matches_expected_failures"] = row["failed_checks"] == expected_failed
                else:
                    row = evaluate_arm(case_id, arm, target)
                    row["matches_expected_failures"] = None
                if note:
                    row["note"] = note
                rows.append(row)

    lookup = {(r["case_id"], r["arm"]): r for r in rows}
    checks = {
        "omitted_loses_process_checks": all(
            lookup[(c, "steps_omitted")]["objective_score"] < 60 for c in CASES),
        "backfilled_reaches_full_marks": all(
            lookup[(c, "steps_backfilled")]["objective_score"] == 60 for c in CASES),
        "consistent_wrong_value_loses_exact_value_checks": all(
            lookup[(c, "self_consistent_wrong_value")]["matches_expected_failures"]
            for c in CASES),
    }
    report = {
        "schema": "tx-harness/adversarial-artifact-audit/v1",
        "question": "跳步但伪造证据（最终文件自洽、步骤文件事后补写）能否通过 T03-M/T05-M 的冻结判卷器？",
        "answer": ("能。步骤文件是普通 JSON，可由最终产物反推；判卷器不看写入顺序、时间戳或调用轨迹，"
                   "所以“先做最终产物、再补步骤”与“真按步骤做”在产物层无法区分，两臂同为 60/60。"
                   "但伪造者仍不能靠自洽拿满分：一个业务值改错（三方自洽）会精确失去绑定该值的检查。"
                   "因此这 60 分只能称“产物一致性分”，不是过程真实性，也不能替代原生调用证据。"),
        "arms": rows,
        "checks": checks,
        "native_call_evidence": {
            "state": "not_obtained",
            "would_require": "产品侧工具调用/请求事件或可核验的执行轨迹（时间戳、调用序号、错误回传）",
            "current_products": "五款均未取得；仅 DSH 与 Codex 在固定响应轨道有受控事件，且不覆盖这两条变体",
        },
        "limits": ("只测两条冻结契约、只测产物层；三条臂均由脚本从冻结输入确定性构造，不是产品运行。"
                   "本审计不能证明真实产品会或不会跳步，只能界定这套判卷器能区分什么。"),
        "passed": all(checks.values()),
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只与冻结报告比对")
    args = parser.parse_args(argv)
    report = build_report()
    if args.check:
        frozen = json.loads(REPORT.read_text(encoding="utf-8"))
        if json.dumps(frozen, sort_keys=True, ensure_ascii=False) != \
                json.dumps(report, sort_keys=True, ensure_ascii=False):
            print("FAIL 报告与重算结果不一致")
            return 1
        if not report["passed"]:
            print("FAIL 三条臂的预期不成立")
            return 1
        print("adversarial-artifacts: 6 臂，三个判据全部成立")
        return 0
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in report["arms"]:
        print(f"{row['case_id']:6s} {row['arm']:28s} {row['objective_score']:5.1f}/60 "
              f"failed={row['failed_checks']}")
    print("checks:", json.dumps(report["checks"], ensure_ascii=False))
    print("passed:", report["passed"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
