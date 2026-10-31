"""Build and audit the week-three run ledger.

    python -X utf8 scripts/ledger.py selftest     # capture the offline suite result
    python -X utf8 scripts/ledger.py build        # regenerate ledger/* and the table
    python -X utf8 scripts/ledger.py --check      # read-only audit, no product run
    python -X utf8 scripts/ledger.py reproduce CL-01
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ledger_sources as S  # noqa: E402
import independent_check  # noqa: E402

LEDGER = ROOT / "ledger"
TABLE_MD = ROOT / "reports/week3/formal-table.md"
FIVE_PARTS = ("observation", "evidence", "explanation", "unexcluded", "reproducible_experiment")

REVISION_SPECS = (
    {"id": "GR-01", "rule_id": "CSV_STRICT", "near_miss": "N6", "positive": "G1",
     "before": "legacy artifact checks only; a damaged CSV field was recovered by the default parser",
     "after": "legacy checks AND a strict quote-aware parse of every csv_rows target"},
    {"id": "GR-02", "rule_id": "T03_CHANGELOG_KEYS", "near_miss": "N7", "positive": "G3",
     "before": "legacy sub-set comparison accepted an extra top-level key",
     "after": "the change log top-level key set must equal the two required sections"},
    {"id": "GR-03", "rule_id": "DECODED_FORBIDDEN_TEXT", "near_miss": "N8", "positive": "G5",
     "before": "a raw-text search missed a marker written as a JSON unicode escape",
     "after": "decoded JSON strings and keys are inspected in addition to the raw text"},
)

RUN_FIELDS = ("run_id", "account", "task", "product", "model", "tools", "permissions",
              "skill_state", "timing", "evidence", "gates", "verdict")


def write(path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def line(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Reproducible experiments cited by the conclusions.
# ---------------------------------------------------------------------------

def reproduce_cl01(records, table):
    return {
        "schema": "tx-harness/reproduce/v1",
        "claim": "CL-01",
        "admission_rule": table["admission_rule"],
        "counts": table["counts"],
        "products": [{key: product[key] for key in
                      ("product_id", "runs", "scored", "pass", "fail", "unknown",
                       "excluded_by_gate", "objective_points", "objective_maximum",
                       "missing_cases")} for product in table["products"]],
        "records": [{"run_id": record["run_id"],
                     "track": record["track"],
                     "verdict": record["verdict"]["state"],
                     "score": record["verdict"]["score_for_aggregate"],
                     "eligible": S.table_eligible(record)}
                    for record in sorted(records, key=lambda item: item["run_id"])
                    if record["account"] == "product_run"],
        "ranking": table["ranking"],
        "ranking_withheld_because": table["ranking_withheld_because"],
    }


CONTROLLED = "public/supplements/controlled-adapter-v1"


def reproduce_cl02():
    arms = []
    for run_id in ("CA11-dsh-error", "CA12-codex-success", "CA13-dsh-success", "CA14-codex-error"):
        folder = f"{CONTROLLED}/{run_id}"
        execution = S.load(f"{folder}/execution.json")
        tool_calls = tool_errors = model_requests = 0
        for event in jsonl(f"{folder}/mcp-events.jsonl"):
            if (event.get("request") or {}).get("method") == "tools/call":
                tool_calls += 1
                payload = json.dumps(event.get("response") or event.get("result") or {},
                                     ensure_ascii=False)
                if '"isError":true' in payload.replace(" ", "") or '"error"' in payload:
                    tool_errors += 1
        model_requests = sum(1 for event in jsonl(f"{folder}/model-events.jsonl")
                             if event.get("kind") == "model_request")
        artifact = f"{folder}/collected/artifact.txt"
        arms.append({
            "run_id": run_id,
            "product_id": execution["product_id"],
            "mode": execution["mode"],
            "exit_code": execution.get("exit_code"),
            "model_requests": model_requests,
            "tool_calls": tool_calls,
            "tool_errors": tool_errors,
            "artifact_sha256": S.sha_file(artifact) if S.exists(artifact) else None,
        })
    success = [arm for arm in arms if arm["mode"] == "success"]
    error = [arm for arm in arms if arm["mode"] == "error"]

    def signature(product):
        return tuple(sorted((arm["mode"], arm["tool_calls"], arm["model_requests"],
                             arm["artifact_sha256"] is None, arm["tool_errors"])
                            for arm in arms if arm["product_id"] == product))

    return {
        "schema": "tx-harness/reproduce/v1",
        "claim": "CL-02",
        "arms": arms,
        "success_artifact_bytes_identical": len({arm["artifact_sha256"] for arm in success}) == 1
        and success[0]["artifact_sha256"] is not None,
        "error_arms_without_artifact": all(arm["artifact_sha256"] is None for arm in error),
        "every_arm_single_tool_call": all(arm["tool_calls"] == 1 for arm in arms),
        "every_arm_exit_zero": all(arm["exit_code"] == 0 for arm in arms),
        "every_arm_two_model_requests": all(arm["model_requests"] == 2 for arm in arms),
        "cross_product_difference_observed": signature("codex") != signature("dsh"),
        "signature_codex": signature("codex"),
        "signature_dsh": signature("dsh"),
    }


def jsonl(relative):
    path = ROOT / relative
    if not path.exists():
        return []
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines() if text.strip()]


def reproduce_cl04():
    import csv
    runs = {}
    for replicate in (1, 2, 3):
        folder = f"public/pilots/dsh-sdk-T05-r{replicate}"
        with open(ROOT / folder / "outputs/invoice_ledger.csv", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        included = [row for row in rows if row["included"].lower() == "true"]
        summary = S.load(f"{folder}/outputs/summary.json")
        first = next(row for row in rows if row["order_id"] == "B001")
        runs[f"r{replicate}"] = {
            "b001_net_cents": int(first["net_cents"]),
            "included_rows": len(included),
            "included_gross_cents": sum(int(row["gross_cents"]) for row in included),
            "included_net_cents": sum(int(row["net_cents"]) for row in included),
            "summary_gross_cents": summary.get("gross_cents"),
            "summary_net_cents": summary.get("net_cents"),
        }
    for value in runs.values():
        value["summary_equals_own_ledger"] = (
            value["summary_gross_cents"] == value["included_gross_cents"]
            and value["summary_net_cents"] == value["included_net_cents"])
    return {
        "schema": "tx-harness/reproduce/v1",
        "claim": "CL-04",
        "expected_b001_net_cents": 8200,
        "runs": runs,
        "only_r1_differs": runs["r2"] == runs["r3"] and runs["r1"] != runs["r2"],
    }


REPRODUCE = {
    "CL-01": lambda: reproduce_cl01(S.build_runs(), S.build_table(S.build_runs())),
    "CL-02": reproduce_cl02,
    "CL-03": lambda: reproduce_cl03(),
    "CL-04": reproduce_cl04,
}


REPEAT_CASES = {
    "T01": ("dsh-sdk-T01-r1", "dsh-sdk-T01-r2", "dsh-sdk-T01-r3"),
    "T02": ("dsh-sdk-T02-r1", "dsh-sdk-T02-r2", "dsh-sdk-T02-r3"),
    "T03": ("dsh-sdk-T03-r1", "dsh-sdk-T03-r2", "dsh-sdk-T03-r3"),
    "T05": ("dsh-sdk-T05-r1", "dsh-sdk-T05-r2", "dsh-sdk-T05-r3"),
}


def reproduce_cl03():
    result = {"schema": "tx-harness/reproduce/v1", "claim": "CL-03", "tasks": {}}
    for case, runs in REPEAT_CASES.items():
        required = S.load(f"cases/{case}/case.json").get("required_outputs") or []
        rows = []
        for name in runs:
            verification = S.load(f"public/pilots/{name}/deterministic-verification.json")
            base = ROOT / "public/pilots" / name / "outputs"
            files = {}
            for path in sorted(base.rglob("*")):
                key = path.relative_to(base).as_posix()
                if path.is_file() and (not required or key in required):
                    files[key] = S.sha_file(path)
            rows.append({"run_id": name,
                         "score": verification.get("objective_score"),
                         "passed": bool(verification.get("all_checks_passed")),
                         "checks": len(verification.get("checks", [])),
                         "files": files})
        names = sorted({key for row in rows for key in row["files"]})
        byte_identical = {key: len({row["files"][key] for row in rows}) == 1 for key in names}
        semantic_identical = {}
        for key in names:
            if not key.endswith(".json"):
                continue
            digests = set()
            for row in rows:
                data = S.load(f"public/pilots/{row['run_id']}/outputs/{key}")
                digests.add(S.sha_bytes(S.canonical(data)))
            semantic_identical[key] = len(digests) == 1
        result["tasks"][case] = {
            "runs": rows,
            "scores": [row["score"] for row in rows],
            "all_passed": all(row["passed"] for row in rows),
            "byte_identical_across_three": byte_identical,
            "semantic_identical_across_three": semantic_identical,
        }
    return result


def experiment_hash(claim) -> str:
    return S.sha_bytes(S.canonical(REPRODUCE[claim]()))


# ---------------------------------------------------------------------------
# Markdown projection for the written report.
# ---------------------------------------------------------------------------

def table_markdown(table):
    out = []
    out.append("# 正式比较表（由台账生成）\n\n")
    out.append("本页由 `python -X utf8 scripts/ledger.py build` 从 `ledger/runs.jsonl` 直接生成，"
               "不手工编辑。纳入条件：`account=product_run` 且规则冻结、题面有效、证据有效、无污染。"
               "未知裁定不计分、不记失败，也不从已评部分折算满分。表内“产物分”是 0–60 的文件契约分，"
               "不含人工过程维度。\n\n")
    counts = table["counts"]
    out.append(f"- 产品运行记录：{counts['product_runs']}（端到端 {counts['end_to_end']}、"
               f"固定响应主臂 {counts['controlled_contract']}、接入校准 {counts['calibration']}、"
               f"原生桌面 {counts['native_ui_probe']}、同题重复 {counts['repeat_batch']}）\n")
    out.append(f"- 通过四道门槛：{counts['comparison_eligible']}；"
               f"被门槛挡下：{counts['comparison_excluded']}；"
               f"未知裁定：{counts['unknown_verdicts']}\n")
    out.append("\n## 五题端到端：逐产品汇总\n\n")
    out.append("| 产品 | 运行 | 已评 | 通过 | 失败 | 未知 | 门槛挡下 | 产物分 | 缺题 |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for product in table["products"]:
        missing = "、".join(product["missing_cases"]) or "无"
        out.append(f"| {product['label']} | {product['runs']} | {product['scored']} | "
                   f"{product['pass']} | {product['fail']} | {product['unknown']} | "
                   f"{product['excluded_by_gate']} | {product['objective_points']:g}/"
                   f"{product['objective_maximum']:g} | {missing} |\n")
    out.append("\n排名：**不发布**（`null`）。原因：\n\n")
    for reason in table["ranking_withheld_because"]:
        out.append(f"- {reason}\n")
    out.append("\n## 五题端到端：逐次记录\n\n")
    out.append("| 产品 | 题 | 运行 | 裁定 | 产物分 | 证据等级 | 门槛 |\n")
    out.append("|---|---|---|---|---:|---|---|\n")
    for row in table["main_rows"]:
        gates = "".join("✓" if row["gates"][name] else "✗" for name in
                        ("rule_frozen", "prompt_valid", "evidence_valid", "uncontaminated"))
        score = "—" if row["objective_score"] is None else f"{row['objective_score']:g}"
        out.append(f"| {S.PRODUCT_LABELS[row['product_id']]} | {row['case_id']} | "
                   f"`{row['run_id']}` | {row['verdict']} | {score} | {row['evidence_grade']} | "
                   f"{gates} |\n")
    out.append("\n门槛顺序为：规则冻结 / 题面有效 / 证据有效 / 无污染。\n")
    out.append("\n## 固定响应工具契约（受控组件轨道）\n\n")
    out.append("模型响应由本地脚本固定，无神经推理；四臂同一工具、同一参数。\n\n")
    out.append("| 产品 | 运行 | 模式 | 裁定 | 证据等级 |\n|---|---|---|---|---|\n")
    for row in table["controlled_rows"]:
        out.append(f"| {S.PRODUCT_LABELS[row['product_id']]} | `{row['run_id']}` | "
                   f"{row['run_id'].split('-')[-1]} | {row['verdict']} | {row['evidence_grade']} |\n")
    out.append("\n## 接入校准（不计入比较）\n\n")
    out.append("| 产品 | 运行 | 裁定 | 证据等级 |\n|---|---|---|---|\n")
    for row in table["calibration_rows"]:
        out.append(f"| {S.PRODUCT_LABELS[row['product_id']]} | `{row['run_id']}` | "
                   f"{row['verdict']} | {row['evidence_grade']} |\n")
    out.append("\n## 重复批（同题多次，测稳定性，不加题量）\n\n")
    out.append("| 产品 | 运行 | 题 | 裁定 | 产物分 | 证据等级 |\n|---|---|---|---|---:|---|\n")
    for row in table["repeat_rows"]:
        score = "—" if row["objective_score"] is None else f"{row['objective_score']:g}"
        out.append(f"| {S.PRODUCT_LABELS[row['product_id']]} | `{row['run_id']}` | "
                   f"{row['case_id']} | {row['verdict']} | {score} | {row['evidence_grade']} |\n")
    out.append("\n重复批只用于回答“同一产品同一题重复跑是否稳定”，不增加题量、不改变上面的"
               "五题汇总；结果见 [CL-03](../../ledger/conclusions/CL-03.json)。\n")
    out.append("\n校准未走通共享工具调用，按未知保留，不记产品失败，也不进入上面的比较表。\n")
    return "".join(out).encode("utf-8")


# ---------------------------------------------------------------------------
# Grader revision archive: one entry per validity guard, each carrying the six
# things the new requirement asks for.
# ---------------------------------------------------------------------------

CODE_DIR = LEDGER / "revisions/code"


def build_revisions():
    index = revision_index()
    write(LEDGER / "revisions/independent-check.json",
          S.canonical(independent_check.run()))
    write(CODE_DIR / "legacy-core.py", (ROOT / "harness_eval/core.py").read_bytes())
    write(CODE_DIR / "grader-v3.py", (ROOT / "evaluation_v3/grader.py").read_bytes())
    for revision in index["revisions"]:
        for item in revision["archived_files"]:
            write(ROOT / item["archive"], (ROOT / item["source"]).read_bytes())
    write(LEDGER / "revisions/index.json", S.canonical(index))
    return index


def revision_index():
    audit = S.load("reports/grader-audit-v3.json")
    examples = {item["example_id"]: item for item in audit["examples"]}
    ablations = audit["ablations"]
    historical = audit["historical_artifact_rechecks"]
    rules = S.load("supplements/grader-v3/rules.json")
    independent = independent_check.run()

    revisions = []
    for spec in REVISION_SPECS:
        rule = spec["rule_id"]
        positive = examples[spec["positive"]]
        near = examples[spec["near_miss"]]
        if rule not in {guard["rule_id"] for guard in positive["validity_guards"]}:
            raise SystemExit(f"{spec['id']}: positive control does not exercise {rule}")
        example_dir = f"public/grader-audit-v3/{near['example_id']}"
        archived = [planned_archive(f"{example_dir}/example.json",
                                    f"ledger/revisions/{spec['id']}/near-miss/example.json"),
                    planned_archive(f"public/grader-audit-v3/{positive['example_id']}/example.json",
                                    f"ledger/revisions/{spec['id']}/positive/example.json")]
        for relative in near["changed_output_paths_from_golden"]:
            archived.append(planned_archive(f"{example_dir}/outputs/{relative}",
                                            f"ledger/revisions/{spec['id']}/near-miss/{relative}"))
        related = [item for item in ablations
                   if item["example_id"] == near["example_id"]
                   and set(item["disabled_rules"]) == {rule}]
        failures = [row["run_id"] for row in historical
                    if row["legacy_accepted"] and any(
                        failure.get("rule_id") == rule and not failure.get("passed")
                        for failure in row.get("guard_failures", []))]
        revisions.append({
            "id": spec["id"],
            "rule_id": rule,
            "rule_text": rules["rules"][rule],
            "registered_on": rules["registered_on"],
            "scope": "artifact validity guard; no new weighted score, no sealed score rewritten",
            "before": {
                "behavior": spec["before"],
                "code": {"path": "harness_eval/core.py",
                         "sha256": S.sha_file("harness_eval/core.py"),
                         "archived": "ledger/revisions/code/legacy-core.py"},
                "rule_snapshot": "absent: the legacy path has no validity guard for this condition",
            },
            "after": {
                "behavior": spec["after"],
                "code": {"path": "evaluation_v3/grader.py",
                         "sha256": S.sha_file("evaluation_v3/grader.py"),
                         "archived": "ledger/revisions/code/grader-v3.py"},
                "rules": {"path": "supplements/grader-v3/rules.json",
                          "sha256": S.sha_file("supplements/grader-v3/rules.json"),
                          "value": rules["rules"][rule]},
            },
            "positive_control": {
                "example": positive["example_id"],
                "case_id": positive["case_id"],
                "expected_accepted": positive["expected_accepted"],
                "legacy_accepted": positive["legacy_accepted"],
                "v3_accepted": positive["v3_accepted"],
                "note": "the same correct answer is still accepted after the revision",
            },
            "near_miss": {
                "example": near["example_id"],
                "case_id": near["case_id"],
                "mutation": near["mutation"],
                "expected_accepted": near["expected_accepted"],
                "legacy_accepted": near["legacy_accepted"],
                "v3_accepted": near["v3_accepted"],
                "note": "the answer is correct except for the one condition this revision guards",
            },
            "ablation": {
                "checks": related,
                "reading": "disabling only this rule restores acceptance, so the verdict is caused "
                           "by this guard and not by a neighbouring check",
            },
            "independent_acceptance": {
                "method": independent["method"],
                "artifact": "ledger/revisions/independent-check.json",
                "sha256": S.sha_bytes(S.canonical(independent)),
                "examples": independent["examples"],
                "guard_verdicts_compared": independent["guard_verdicts_compared"],
                "agrees": independent["agrees"],
                "disagreements": independent["disagreements"],
            },
            "historical_recompute_impact": {
                "recomputed": len(historical),
                "newly_rejected": len(failures),
                "run_ids": failures,
                "reading": "no published run changes acceptance state under this guard; old scores "
                           "stay sealed",
            },
            "archived_files": archived,
            "files": ["ledger/revisions/code/legacy-core.py", "ledger/revisions/code/grader-v3.py",
                      "ledger/revisions/independent-check.json"]
                     + [item["archive"] for item in archived],
        })
    return {
        "schema": "tx-harness/grader-revision-archive/v1",
        "rule_source": {"path": "supplements/grader-v3/rules.json",
                        "sha256": S.sha_file("supplements/grader-v3/rules.json"),
                        "schema": rules["schema"]},
        "audit_source": {"path": "reports/grader-audit-v3.json",
                         "sha256": S.sha_file("reports/grader-audit-v3.json")},
        "counting_rule": "a revision, a synthetic answer and a product run are three different "
                         "things and never share a denominator",
        "revisions": revisions,
    }


def planned_archive(source_path, archive_path):
    data = (ROOT / source_path).read_bytes()
    return {"source": source_path, "archive": archive_path, "sha256": S.sha_bytes(data),
            "bytes": len(data)}


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    records = S.build_runs()
    table = S.build_table(records)
    accounts = S.build_accounts(records)
    write(LEDGER / "runs.jsonl", b"".join(line(record) for record in records))
    write(LEDGER / "formal-table.json", S.canonical(table))
    write(LEDGER / "accounts.json", S.canonical(accounts))
    write(TABLE_MD, table_markdown(table))
    build_revisions()
    write_manifest(records)
    print(f"records={len(records)} eligible={table['counts']['comparison_eligible']} "
          f"excluded={table['counts']['comparison_excluded']} "
          f"unknown={table['counts']['unknown_verdicts']}")


def write_manifest(records):
    curated = ["ledger/unknowns.json", "ledger/conclusions/CL-01.json",
               "ledger/conclusions/CL-02.json", "ledger/revisions/index.json"]
    for relative in curated:
        if not (ROOT / relative).exists():
            raise SystemExit("missing curated ledger file: " + relative)
    revisions = S.load("ledger/revisions/index.json")
    files = ["ledger/runs.jsonl", "ledger/formal-table.json", "ledger/accounts.json",
             "ledger/self-test.json", *curated]
    for item in revisions["revisions"]:
        files.extend(item["files"])
    sources = sorted({"reports/evaluation-v2.json", "supplements/week2/executions.json",
                      "supplements/grader-v3/rules.json", "evaluation_v3/grader.py",
                      "harness_eval/core.py", "cases/T01/case.json", "cases/T02/case.json",
                      "cases/T03/case.json", "cases/T04/case.json", "cases/T05/case.json",
                      "public/supplements/gui-controls-v1/observations.json",
                      "public/pilots/dsh-sdk-T01-r2/run-metadata.json",
                      "public/pilots/dsh-sdk-T01-r3/run-metadata.json",
                      "reports/grader-audit-v3.json"})
    manifest = {
        "schema": "tx-harness/ledger-manifest/v1",
        "generation_basis": "deterministic offline derivation; no clock, no product run, "
                            "no private collection directory",
        "counts": {"records": len(records)},
        "files": [{"path": S.rel(relative), "sha256": S.sha_file(relative),
                   "bytes": (ROOT / relative).stat().st_size} for relative in files
                  if (ROOT / relative).exists()],
        "sources": [{"path": relative, "sha256": S.sha_file(relative)} for relative in sources],
    }
    write(LEDGER / "manifest.json", S.canonical(manifest))


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class Audit:
    def __init__(self):
        self.problems = []
        self.notes = []

    def require(self, condition, message):
        if not condition:
            self.problems.append(message)
        return bool(condition)

    def note(self, message):
        self.notes.append(message)


def check():
    audit = Audit()
    records = S.build_runs()
    table = S.build_table(records)
    accounts = S.build_accounts(records)

    expected = {
        "ledger/runs.jsonl": b"".join(line(record) for record in records),
        "ledger/formal-table.json": S.canonical(table),
        "ledger/accounts.json": S.canonical(accounts),
        "reports/week3/formal-table.md": table_markdown(table),
    }
    revisions = revision_index()
    expected["ledger/revisions/index.json"] = S.canonical(revisions)
    expected["ledger/revisions/independent-check.json"] = S.canonical(independent_check.run())
    for relative, data in expected.items():
        path = ROOT / relative
        if not audit.require(path.exists(), "missing generated file: " + relative):
            continue
        if not audit.require(path.read_bytes() == data,
                             "generated file drifted from its sources: " + relative):
            continue
        audit.note("matches sources: " + relative)

    check_records(audit, records)
    check_table(audit, records, table)
    check_accounts(audit, records, accounts)
    check_unknowns(audit, records)
    check_conclusions(audit, records, table)
    check_revisions(audit)
    check_manifest(audit)

    for note in audit.notes:
        print("ok  " + note)
    for problem in audit.problems:
        print("FAIL " + problem)
    print(f"\n{len(audit.notes)} checks passed, {len(audit.problems)} failed")
    return audit.problems


def check_records(audit, records):
    seen = set()
    for record in records:
        tag = record["run_id"]
        for field in RUN_FIELDS:
            audit.require(field in record, f"{tag}: missing field {field}")
        audit.require(record["schema"] == "tx-harness/run-record/v1", f"{tag}: schema label")
        audit.require(tag not in seen, f"{tag}: duplicate run id")
        seen.add(tag)
        audit.require(record["account"] in S.ACCOUNTS, f"{tag}: unknown account")
        audit.require(record["track"] in S.TRACKS, f"{tag}: unknown track")
        audit.require(bool(record["task"]["case_id"]), f"{tag}: empty case id")
        audit.require(len(record["task"]["case_sha256"]) == 64, f"{tag}: case hash missing")
        audit.require(len(record["task"]["prompt_sha256"] or "") == 64,
                      f"{tag}: prompt hash missing (题目版本必须可定位)")
        # A field may be unknown only with an explicit reason.
        if record["model"]["label"] in (None, "", "unknown"):
            audit.require(bool(record["model"]["reason"]), f"{tag}: model unknown without reason")
        if record["tools"]["state"] == "unknown":
            audit.require(bool(record["tools"]["reason"]), f"{tag}: tools unknown without reason")
        if record["permissions"].get("label") in (None, "", "unknown"):
            audit.require(bool(record["permissions"].get("reason")),
                          f"{tag}: permissions unknown without reason")
        if record["skill_state"].get("label") in (None, "", "unknown"):
            audit.require(bool(record["skill_state"].get("reason")),
                          f"{tag}: skill state unknown without reason")
        if record["product"].get("version") in (None, "", "unknown"):
            audit.require(bool(record["product"].get("version_reason")),
                          f"{tag}: product version unknown without reason")
        if record["timing"]["started_at"] is None:
            audit.require(bool(record["timing"]["reason"]), f"{tag}: timing unknown without reason")
        # Unknown is never a failure and never a score.
        if record["verdict"]["state"] == "unknown":
            audit.require(record["verdict"]["score_for_aggregate"] is None,
                          f"{tag}: unknown verdict carries a score")
        if record["verdict"]["state"] == "invalid":
            audit.require(record["verdict"]["score_for_aggregate"] is None,
                          f"{tag}: invalid run carries a score")
        if record["verdict"]["state"] in ("pass", "fail"):
            if record["track"] in ("formal_product_end_to_end", "repeat_batch"):
                audit.require(record["verdict"]["score_for_aggregate"] is not None,
                              f"{tag}: scored verdict without score")
            else:
                audit.require(record["verdict"]["score_for_aggregate"] is None,
                              f"{tag}: contract track must not carry an artifact score")
        # Every evidence file must still hash to the recorded value.
        for item in record["evidence"]["files"]:
            audit.require(S.exists(item["path"]), f"{tag}: missing evidence {item['path']}")
            if S.exists(item["path"]):
                audit.require(S.sha_file(item["path"]) == item["sha256"],
                              f"{tag}: evidence hash drift {item['path']}")
        for item in record["sources"]:
            audit.require(S.exists(item["path"]), f"{tag}: missing source {item['path']}")
    audit.require(len({record["task"]["case_id"] for record in records
                       if record["track"] == "formal_product_end_to_end"}) == 5,
                  "end-to-end track does not cover five tasks")
    audit.note(f"run records: {len(records)} unique ids, all ten mandated fields present")


def check_table(audit, records, table):
    rows = [record for record in records if record["account"] == "product_run"]
    main_rows = [record for record in rows if record["track"] == "formal_product_end_to_end"]
    audit.require(len(table["main_rows"]) == len(main_rows), "table main rows incomplete")
    for row in table["main_rows"]:
        audit.require(row["table_eligible"], f"table contains an ineligible run: {row['run_id']}")
        audit.require(all(row["gates"].values()), f"table row with failing gate: {row['run_id']}")
        if row["verdict"] == "unknown":
            audit.require(row["objective_score"] is None, f"table scores unknown row {row['run_id']}")
    # Aggregates must exclude unknown verdicts from numerator and denominator.
    for product in table["products"]:
        owned = [record for record in main_rows
                 if record["product"]["product_id"] == product["product_id"]]
        scored = [record for record in owned if record["verdict"]["state"] in ("pass", "fail")]
        audit.require(product["scored"] == len(scored),
                      f"{product['product_id']}: scored count mismatch")
        audit.require(product["pass"] + product["fail"] == product["scored"],
                      f"{product['product_id']}: pass+fail != scored")
        audit.require(product["scored"] + product["unknown"] + product["excluded_by_gate"]
                      == product["runs"], f"{product['product_id']}: coverage does not reconcile")
        audit.require(product["objective_points"] == sum(
            record["verdict"]["score_for_aggregate"] or 0 for record in scored),
            f"{product['product_id']}: objective points mismatch")
        audit.require(product["ranking"] is None, f"{product['product_id']}: unexpected ranking")
    audit.require(table["ranking"] is None, "ranking published without the stricter gate")
    audit.require(bool(table["ranking_withheld_because"]), "withheld ranking without reasons")
    audit.require(table["counts"]["unknown_verdicts"] == sum(
        1 for record in rows if record["verdict"]["state"] == "unknown"),
        "unknown verdict count mismatch")
    audit.note("table admission rule holds; unknown verdicts excluded from every aggregate")


def check_accounts(audit, records, accounts):
    for name in S.ACCOUNTS:
        audit.require(name in accounts, "missing account: " + name)
    product_rows = [record for record in records if record["account"] == "product_run"]
    audit.require(accounts["product_run"]["entries"] == len(product_rows),
                  "product_run ledger does not match the run file")
    audit.require(accounts["product_run"]["entries"] == len(
        jsonl("ledger/runs.jsonl")), "product_run ledger does not match ledger/runs.jsonl")
    if "recompute" in accounts["product_run"]:
        audit.require(accounts["product_run"]["recompute"]["kind"] == "lines",
                      "product run recompute kind")
    for name, account in accounts.items():
        if name.startswith("_"):
            continue
        entries = []
        if "recompute" in account:
            entries.append(account["recompute"])
        entries.extend(account.get("items", []))
        for spec in entries:
            verify_count(audit, name, spec)
    # The six ledgers must not be presented as one additive workload.
    audit.require("no_cross_account_sum" in accounts["_rules"], "missing cross-account rule")
    self_test = accounts["self_test"]
    if S.exists(self_test["artifact"]):
        payload = S.load(self_test["artifact"])
        audit.require(payload["failures"] == 0 and payload["errors"] == 0,
                      f"self_test: captured suite is not green "
                      f"({payload['failures']} failures, {payload['errors']} errors)")
        audit.require(payload["total"] == sum(item["tests"] for item in payload["modules"]),
                      "self_test: module totals do not add up to the captured total")
    audit.require(accounts["bare_model_probe"]["entries"] == 0,
                  "bare model probe ledger is not empty")
    audit.require(bool(accounts["bare_model_probe"].get("stop_condition")),
                  "empty bare model probe without a stop condition")
    audit.require(accounts["interface_preflight"]["tasks_counted"] == 0,
                  "interface preflight counted product tasks")
    audit.note("six ledgers verified independently; no cross-account total exists")


def verify_count(audit, name, spec):
    artifact = spec["artifact"]
    if not audit.require(S.exists(artifact), f"{name}: missing artifact {artifact}"):
        return
    kind = spec.get("kind", "value")
    if kind == "lines":
        value = len((ROOT / artifact).read_text(encoding="utf-8").splitlines())
    else:
        value = S.load(artifact)
        if spec.get("pointer"):
            value = S.pointer(value, spec["pointer"])
        if kind == "length":
            value = len(value)
    if spec.get("expected") is not None:
        audit.require(value == spec["expected"],
                      f"{name}: {spec.get('label')} expected {spec['expected']} got {value}")


def check_unknowns(audit, records):
    register = S.load("ledger/unknowns.json")
    previous = S.load("supplements/week2/unknowns.json")
    previous_ids = {item["id"] for item in previous["items"]}
    current_ids = {item["id"] for item in register["items"]}
    audit.require(previous_ids <= current_ids,
                  "previously registered unknowns disappeared: " + str(sorted(previous_ids - current_ids)))
    for item in register["items"]:
        tag = item["id"]
        for field in ("question", "state", "impact", "next_action", "stop_condition"):
            audit.require(bool(item.get(field)), f"{tag}: empty {field}")
        audit.require(item.get("scored") is False, f"{tag}: unknown is not marked unscored")
        audit.require(item.get("denominator") == "excluded",
                      f"{tag}: unknown is not excluded from the denominator")
        for path in item.get("evidence", []):
            audit.require(S.exists(path), f"{tag}: missing evidence {path}")
        for run_id in item.get("run_ids", []):
            audit.require(any(record["run_id"] == run_id for record in records),
                          f"{tag}: cites an unknown run {run_id}")
    run_ids = {record["run_id"] for record in records}
    audit.require({"W02-window-reopen", "WBC00-workbuddy-calibration",
                   "WBC01-workbuddy-calibration", "WBC02-workbuddy-calibration"} <= run_ids,
                  "unknown-bearing runs are missing from the ledger")
    audit.note(f"unknown register: {len(register['items'])} items, all with impact/next/stop")


def check_conclusions(audit, records, table):
    conclusions = sorted((LEDGER / "conclusions").glob("CL-*.json"))
    audit.require(len(conclusions) >= 2, "fewer than two five-part conclusions")
    for path in conclusions:
        conclusion = json.loads(path.read_text(encoding="utf-8"))
        tag = conclusion.get("id", path.name)
        for part in FIVE_PARTS:
            audit.require(bool(conclusion.get(part)), f"{tag}: empty {part}")
        audit.require(conclusion.get("schema") == "tx-harness/conclusion/v1", f"{tag}: schema")
        for item in conclusion.get("evidence", []):
            if not audit.require(S.exists(item["path"]), f"{tag}: missing evidence {item['path']}"):
                continue
            audit.require(S.sha_file(item["path"]) == item["sha256"],
                          f"{tag}: evidence hash drift {item['path']}")
            if item.get("pointer"):
                try:
                    S.pointer(S.load(item["path"]), item["pointer"])
                except (KeyError, IndexError, TypeError):
                    audit.problems.append(f"{tag}: pointer does not resolve {item['path']}"
                                          f"{item['pointer']}")
        for item in conclusion.get("unexcluded", []):
            audit.require(bool(item.get("factor")) and bool(item.get("impact")),
                          f"{tag}: an unexcluded factor lacks factor/impact")
        experiment = conclusion["reproducible_experiment"]
        audit.require(experiment["claim"] in REPRODUCE, f"{tag}: experiment not reproducible")
        if experiment["claim"] in REPRODUCE:
            fresh = REPRODUCE[experiment["claim"]]()
            digest = S.sha_bytes(S.canonical(fresh))
            audit.require(digest == experiment["expected_output_sha256"],
                          f"{tag}: reproducible experiment output changed")
    audit.note("conclusions carry all five parts and replay to the frozen hash")


def check_revisions(audit):
    index = S.load("ledger/revisions/index.json")
    audit_report = S.load("reports/grader-audit-v3.json")
    by_example = {item["example_id"]: item for item in audit_report["examples"]}
    ablations = audit_report["ablations"]
    for revision in index["revisions"]:
        tag = revision["id"]
        for relative in revision["files"]:
            audit.require(S.exists(relative), f"{tag}: missing archived file {relative}")
        for item in revision["archived_files"]:
            if not audit.require(S.exists(item["archive"]), f"{tag}: missing {item['archive']}"):
                continue
            audit.require(S.sha_file(item["archive"]) == item["sha256"],
                          f"{tag}: archived bytes drifted {item['archive']}")
            audit.require(S.sha_file(item["source"]) == item["sha256"],
                          f"{tag}: source bytes changed under {item['source']}")
        code = revision["after"]["code"]
        audit.require(S.sha_file(code["archived"]) == code["sha256"],
                      f"{tag}: archived after-code differs from evaluation_v3/grader.py")
        audit.require(S.sha_file(revision["before"]["code"]["archived"])
                      == revision["before"]["code"]["sha256"],
                      f"{tag}: archived before-code differs from harness_eval/core.py")
        rule = revision["rule_id"]
        audit.require(rule in S.load("supplements/grader-v3/rules.json")["rules"],
                      f"{tag}: unknown rule {rule}")
        positive = revision["positive_control"]
        near = revision["near_miss"]
        audit.require(positive["legacy_accepted"] is True and positive["v3_accepted"] is True,
                      f"{tag}: positive control does not survive the revision")
        audit.require(near["legacy_accepted"] is True and near["v3_accepted"] is False,
                      f"{tag}: near-miss does not separate before from after")
        audit.require(near["expected_accepted"] is False, f"{tag}: near-miss marked expected-pass")
        published_positive = by_example[positive["example"]]
        published_near = by_example[near["example"]]
        audit.require(published_positive["v3_matches_expected"]
                      and published_near["v3_matches_expected"],
                      f"{tag}: published example expectations disagree")
        related = [item for item in ablations
                   if item["example_id"] == near["example"]
                   and set(item["disabled_rules"]) == {rule}]
        audit.require(bool(related), f"{tag}: no single-rule ablation for the near-miss")
        if related:
            audit.require(related[0]["accepted"] is True,
                          f"{tag}: disabling only this rule did not restore acceptance")
        acceptance = revision["independent_acceptance"]
        audit.require(acceptance["agrees"] is True, f"{tag}: independent acceptance disagrees")
        audit.require(acceptance["examples"] == audit_report["counts"]["synthetic_examples"],
                      f"{tag}: independent acceptance did not cover every example")
        audit.require(acceptance["sha256"] == S.sha_file(acceptance["artifact"]),
                      f"{tag}: independent acceptance artifact drifted")
        impact = revision["historical_recompute_impact"]
        audit.require(impact["recomputed"] == audit_report["counts"]["historical_artifact_rechecks"],
                      f"{tag}: historical recompute incomplete")
        audit.require(impact["newly_rejected"] == 0,
                      f"{tag}: historical runs changed acceptance under this guard")
    audit.note(f"grader revisions archived: {len(index['revisions'])} with before/after code, "
               "positive control, near-miss, independent acceptance and historical impact")


def check_manifest(audit):
    manifest = S.load("ledger/manifest.json")
    for item in manifest["files"] + manifest["sources"]:
        if not audit.require(S.exists(item["path"]), f"manifest: missing {item['path']}"):
            continue
        audit.require(S.sha_file(item["path"]) == item["sha256"],
                      f"manifest: hash drift {item['path']}")
    audit.note(f"manifest binds {len(manifest['files'])} ledger files and "
               f"{len(manifest['sources'])} sources")


# ---------------------------------------------------------------------------
# Self test capture
# ---------------------------------------------------------------------------

def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def selftest():
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    modules = {}
    for test in iter_tests(suite):
        identifier = getattr(test, "id", None)
        if not callable(identifier):
            continue
        parts = identifier().split(".")
        module = parts[1] if parts[0] == "tests" else parts[0]
        modules[module] = modules.get(module, 0) + 1
    result = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
    payload = {
        "schema": "tx-harness/self-test/v1",
        "command": "python -X utf8 -m unittest discover -s tests -v",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "total": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "modules": [{"module": name, "tests": count} for name, count in sorted(modules.items())],
        "note": "captured artifact; re-run the command to reproduce the counts. It proves the "
                "suite passed at capture time, not that no other work happened.",
    }
    write(LEDGER / "self-test.json", S.canonical(payload))
    print(f"self-test total={payload['total']} failures={payload['failures']} "
          f"errors={payload['errors']} skipped={payload['skipped']}")
    return 1 if payload["failures"] or payload["errors"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="build",
                        choices=("build", "check", "selftest", "reproduce"))
    parser.add_argument("target", nargs="?")
    parser.add_argument("--check", action="store_true", help="audit without writing")
    args = parser.parse_args(argv)
    if args.check or args.command == "check":
        return 1 if check() else 0
    if args.command == "selftest":
        return selftest()
    if args.command == "reproduce":
        if args.target not in REPRODUCE:
            parser.error("unknown conclusion: " + str(args.target))
        sys.stdout.write(json.dumps(REPRODUCE[args.target](), ensure_ascii=False, indent=2,
                                    sort_keys=True) + "\n")
        return 0
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
