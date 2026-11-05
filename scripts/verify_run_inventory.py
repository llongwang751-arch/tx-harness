"""重建并校验 47 条产品运行的逐条清单：发生日期、入账提交、统计窗口归属。

用法：
    python -X utf8 scripts/verify_run_inventory.py            # 重建 ledger/run-inventory.json 与 .md
    python -X utf8 scripts/verify_run_inventory.py --check    # 只校验，不写文件

校验内容：
  1. inventory 的 run 集合与 ledger/runs.jsonl 完全一致（不多、不少、字段一致）。
  2. 每条运行的 ledger_commit 确实是首次引入该 run_id 的提交（用 git 历史逐提交核对）。
  3. 窗口归属（历史入账 / 第3周新增 / 第4周新增）与发生日期一致。
  4. 生成的 Markdown 表与 JSON 一致。

只读公开文件；需要 git 读取历史，但不改动任何工作区文件。
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "ledger" / "runs.jsonl"
INV_JSON = ROOT / "ledger" / "run-inventory.json"
INV_MD = ROOT / "ledger" / "run-inventory.md"

# 统计窗口：第3周 2026-10-25..31；第4周 2026-11-01..07。
WINDOWS = [
    ("week3", "2026-10-25", "2026-10-31", "第3周新增（10-25至10-31）"),
    ("week4", "2026-11-01", "2026-11-07", "第4周新增（11-01至11-07）"),
]

TRACK_LABELS = {
    "formal_product_end_to_end": "五题端到端",
    "repeat_batch": "同题重复",
    "adapter_calibration": "接入校准",
    "formal_controlled_contract": "固定响应主臂",
    "native_ui_probe": "原生桌面",
}


def load_runs():
    runs = []
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            runs.append(json.loads(line))
    return runs


def occurred_on(run):
    timing = run.get("timing") or {}
    started = timing.get("started_at") or ""
    return started[:10] if started else None


def git_commits_touching_runs():
    out = subprocess.run(
        ["git", "log", "--format=%H %ad", "--date=short", "--", "ledger/runs.jsonl"],
        cwd=ROOT, capture_output=True, check=True, text=True, encoding="utf-8",
    ).stdout
    return [line.split() for line in out.splitlines() if line.strip()]  # 旧→新需反转


def run_ids_at(commit):
    out = subprocess.run(
        ["git", "show", f"{commit}:ledger/runs.jsonl"],
        cwd=ROOT, capture_output=True, check=True, text=True, encoding="utf-8",
    ).stdout
    return {json.loads(line)["run_id"] for line in out.splitlines() if line.strip()}


def first_introducing_commits():
    """返回 run_id -> (short_hash, commit_date)。旧提交在前逐个做差集。"""
    commits = list(reversed(git_commits_touching_runs()))
    mapping = {}
    prev_ids = set()
    for full_hash, date in commits:
        ids = run_ids_at(full_hash)
        for run_id in sorted(ids - prev_ids):
            mapping[run_id] = (full_hash[:7], date)
        prev_ids = ids
    return mapping


def week_label(date):
    for key, lo, hi, label in WINDOWS:
        if lo <= date <= hi:
            return label
    return "历史材料入账（窗口前）"


def build_inventory():
    runs = load_runs()
    mapping = first_introducing_commits()
    entries = []
    for run in runs:
        task = run.get("task") or {}
        date = occurred_on(run)
        short, commit_date = mapping[run["run_id"]]
        product = run.get("product") or {}
        verdict = run.get("verdict") or {}
        score = verdict.get("objective_score")
        state = verdict.get("state")
        verdict_text = (f"{state} {score}/{verdict.get('objective_max')}"
                        if isinstance(score, (int, float)) else str(state))
        entries.append({
            "run_id": run["run_id"],
            "occurred_on": date,
            "track": run.get("track"),
            "track_label": TRACK_LABELS.get(run.get("track"), run.get("track")),
            "account": run.get("account"),
            "product_id": product.get("product_id"),
            "product_label": product.get("label"),
            "task": task.get("case_id") or task.get("id") or task.get("case") or None,
            "verdict_state": state,
            "verdict_score": verdict_text,
            "ledger_commit": short,
            "ledger_commit_date": commit_date,
            "window": week_label(date),
        })
    entries.sort(key=lambda e: (e["occurred_on"] or "", e["run_id"]))
    by_window = collections.Counter(e["window"] for e in entries)
    by_track = collections.Counter(e["track"] for e in entries)
    return {
        "schema": "tx-harness/run-inventory/v1",
        "generated_for": "Issue #1：逐条给出 47 条运行的日期、分类与统计窗口归属",
        "runs_total": len(entries),
        "counts_by_window": dict(by_window),
        "counts_by_track": dict(by_track),
        "runs": entries,
    }


def render_markdown(inv):
    lines = [
        "# 运行逐条清单（47 条）",
        "",
        "由 `scripts/verify_run_inventory.py` 从 `ledger/runs.jsonl` 与 git 历史重建；",
        "`--check` 可复核本表与台账、与入账提交三方一致。窗口归属按运行**发生日期**计，",
        "与按**入账提交日期**计的台账增长（10-31 当天 39→41→45→47）分开陈述，见周报。",
        "",
        "| run_id | 发生日期 | 轨道 | 产品 | 任务 | 判定 | 入账提交 | 窗口归属 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in inv["runs"]:
        lines.append(
            f"| {e['run_id']} | {e['occurred_on']} | {e['track_label']} | {e['product_label']} "
            f"| {e['task'] or '—'} | {e['verdict_score']} | {e['ledger_commit']} | {e['window']} |"
        )
    lines += ["", f"合计 {inv['runs_total']} 条；按窗口："
              + "；".join(f"{k}={v}" for k, v in sorted(inv["counts_by_window"].items()))
              + "。", ""]
    return "\n".join(lines)


def verify(inv):
    problems = []
    runs = load_runs()
    by_id = {r["run_id"]: r for r in runs}
    inv_ids = [e["run_id"] for e in inv["runs"]]
    if len(inv_ids) != len(set(inv_ids)):
        problems.append("inventory 内 run_id 重复")
    if set(inv_ids) != set(by_id):
        problems.append("inventory 与 runs.jsonl 的 run 集合不一致")
    mapping = first_introducing_commits()
    for e in inv["runs"]:
        run = by_id.get(e["run_id"])
        if not run:
            continue
        if occurred_on(run) != e["occurred_on"]:
            problems.append(f"{e['run_id']}: 发生日期与台账不符")
        if run.get("track") != e["track"] or run.get("account") != e["account"]:
            problems.append(f"{e['run_id']}: 轨道/账目与台账不符")
        short, commit_date = mapping.get(e["run_id"], (None, None))
        if e["ledger_commit"] != short or e["ledger_commit_date"] != commit_date:
            problems.append(f"{e['run_id']}: 入账提交与 git 历史不符")
        if week_label(e["occurred_on"]) != e["window"]:
            problems.append(f"{e['run_id']}: 窗口归属与发生日期不符")
    counts = collections.Counter(e["window"] for e in inv["runs"])
    if dict(counts) != inv["counts_by_window"]:
        problems.append("counts_by_window 与明细不符")
    if render_markdown(inv) != INV_MD.read_text(encoding="utf-8"):
        problems.append("run-inventory.md 与 JSON 不一致")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验，不重建")
    args = parser.parse_args(argv)
    if args.check:
        inv = json.loads(INV_JSON.read_text(encoding="utf-8"))
        problems = verify(inv)
        for p in problems:
            print("FAIL", p)
        print(f"run-inventory: {len(inv['runs'])} 条记录，"
              f"{'全部一致' if not problems else str(len(problems)) + ' 处不一致'}")
        return 1 if problems else 0
    inv = build_inventory()
    INV_JSON.write_text(json.dumps(inv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    INV_MD.write_text(render_markdown(inv), encoding="utf-8")
    print(f"重建完成：{inv['runs_total']} 条 -> {INV_JSON.name}, {INV_MD.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
