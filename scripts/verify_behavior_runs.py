"""校验行为协议 v1 的运行登记，防止把没跑的位写成跑过。

    python -X utf8 scripts/verify_behavior_runs.py --check

检查六件事：
  1. 10 个位 = 5 产品 × 2 变体，一一对应，无重复无缺位。
  2. status 只在允许集合里；非 completed 必须写原因。
  3. completed 的位必须在 public/week5 里有证据包，且分数与 manifest 一致。
  4. manifest 里的每个包都在登记里出现（不能有“包在、位不在”的孤儿）。
  5. counts 与逐位统计一致。
  6. 文件标为 post_hoc，不冒充预登记。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "supplements/behavior-protocol-v1/run-register.json"
PACKAGES = ROOT / "public/week5/manifest.json"
PRODUCTS = ("codex", "workbuddy", "dsh", "yuanbao", "doubao")
CASES = ("T03-M", "T05-M")
STATUSES = {"completed", "invalid_run", "environment_invalid", "not_run", "failed", "unknown"}


def check() -> list[str]:
    problems = []
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    slots = register["slots"]
    if register.get("registration_kind") != "post_hoc":
        problems.append("registration_kind 必须标 post_hoc，不许冒充预登记")

    pairs = [(slot["product_id"], slot["case_id"]) for slot in slots]
    expected = [(product, case) for product in PRODUCTS for case in CASES]
    if sorted(pairs) != sorted(expected):
        problems.append(f"实验位不是 5×2 的完整矩阵：{sorted(pairs)}")

    counts = {"planned": len(slots), "completed": 0, "invalid_run": 0,
              "environment_invalid": 0, "not_run": 0, "failed": 0, "unknown": 0}
    for slot in slots:
        status = slot.get("status")
        if status not in STATUSES:
            problems.append(f"{slot.get('slot_id')}: 未知状态 {status}")
            continue
        counts[status] = counts.get(status, 0) + 1
        if status != "completed" and not slot.get("reason"):
            problems.append(f"{slot['slot_id']}: 非 completed 必须写原因")

    packages = {}
    if PACKAGES.is_file():
        manifest = json.loads(PACKAGES.read_text(encoding="utf-8"))
        packages = {p["run_id"]: p for p in manifest["packages"]}
    for slot in slots:
        if slot["status"] != "completed":
            continue
        package = packages.get(slot["slot_id"])
        if not package:
            problems.append(f"{slot['slot_id']}: 登记为 completed，但 public/week5 里没有对应包")
            continue
        if package["case_id"] != slot["case_id"]:
            problems.append(f"{slot['slot_id']}: 包的 case_id 与登记不符")
        if abs(package["objective_score"] - slot["objective_score"]) > 1e-9:
            problems.append(f"{slot['slot_id']}: 分数与包不一致")
        if sorted(package["failed_checks"]) != sorted(slot["failed_checks"]):
            problems.append(f"{slot['slot_id']}: 失败项与包不一致")

    registered = {slot["slot_id"] for slot in slots}
    for run_id in packages:
        if run_id not in registered:
            problems.append(f"public/week5 有未登记的包：{run_id}")

    for key, value in register.get("counts", {}).items():
        if counts.get(key, 0) != value:
            problems.append(f"counts.{key} 记 {value}，逐位统计是 {counts.get(key, 0)}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args(argv)
    problems = check()
    for problem in problems:
        print("FAIL", problem)
    print(f"behavior-runs: {'一致' if not problems else str(len(problems)) + ' 处问题'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
