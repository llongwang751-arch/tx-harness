"""导出并复核第五周两条 Codex 实跑（T03-M / T05-M）的公开证据包。

    python -X utf8 scripts/week5_pilots.py           # 重新导出 public/week5
    python -X utf8 scripts/week5_pilots.py --check   # 校验哈希并重算产物分

公开包只含：运行元数据、原生 JSONL 事件、提交的提示词、交付文件、评分快照。
不含 oracle、不含判卷实现、不含 private。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation_v3.grader import adjudicate  # noqa: E402

RUNS = [
    ("pilot-codex-T03-M-r1", "T03-M", ROOT / "private/codex-pilot/pilot-codex-T03-M-r1"),
    ("pilot-codex-T05-M-r1", "T05-M", ROOT / "private/codex-pilot/pilot-codex-T05-M-r1"),
]
PUBLIC = ROOT / "public/week5"
SCORES = ROOT / "reports/scores"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload(run: Path) -> list[tuple[Path, str]]:
    items = [(run / "meta.json", "meta.json"),
             (run / "events.jsonl", "events.jsonl"),
             (run / "evidence/submitted-prompt.md", "submitted-prompt.md"),
             (run / "workspace/submitted-prompt.md", "submitted-prompt.md"),
             (run / "evidence/initial.stdout.jsonl", "initial.stdout.jsonl"),
             (run / "evidence/launch.json", "launch.json")]
    scored = SCORES / f"{run.name}.json"
    if scored.is_file():
        items.append((scored, "score.json"))
    for path in sorted((run / "workspace/outputs").rglob("*")):
        if path.is_file():
            items.append((path, "outputs/" + path.relative_to(run / "workspace/outputs").as_posix()))
    return items


def build(case_id: str, run: Path) -> dict:
    target = PUBLIC / run.name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    entries = []
    for source, relative in payload(run):
        if not source.is_file():
            continue
        dst = target / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dst)
        entries.append({"path": relative, "sha256": sha(dst), "bytes": dst.stat().st_size})
    score = adjudicate(case_id, target / "outputs")
    readme = target / "README.md"
    readme.write_text(
        f"# Codex CLI × {case_id}（2026-11-13 实跑）\n\n"
        f"原生 `codex exec`，受限权限、单次、1200 秒预算内完成；产物一致性分 "
        f"**{score['legacy_artifact_result']['objective_score']}/60**，"
        f"`accepted={score['accepted']}`。\n\n"
        f"运行元数据见 [meta.json](meta.json)，原生事件见 [initial.stdout.jsonl](initial.stdout.jsonl)，"
        f"提交的提示词见 [submitted-prompt.md](submitted-prompt.md)，交付文件在 [outputs/](outputs)。\n\n"
        "只评产物契约；40 分人工维度未评，`总分 None`。操作方为 AI 代理（CLI 执行），不是人工采集。\n",
        encoding="utf-8")
    entries.append({"path": "README.md", "sha256": sha(readme), "bytes": readme.stat().st_size})
    return {"run_id": run.name, "case_id": case_id,
            "objective_score": score["legacy_artifact_result"]["objective_score"],
            "accepted": score["accepted"],
            "failed_checks": [c["id"] for c in score["legacy_artifact_result"]["checks"]
                              if not c["passed"]],
            "files": entries}


def build_all() -> dict:
    packages = [build(case, run) for _, case, run in RUNS]
    manifest = {
        "schema": "tx-harness/week5-pilots/v1",
        "note": "两条真实运行；GUI 三款的失败方式见 reports/week5/run-log-2026-11-13.md",
        "packages": packages,
        "counts": {"runs": len(packages),
                   "accepted": sum(1 for p in packages if p["accepted"])},
    }
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def check() -> list[str]:
    problems = []
    manifest = json.loads((PUBLIC / "manifest.json").read_text(encoding="utf-8"))
    for package in manifest["packages"]:
        target = PUBLIC / package["run_id"]
        for item in package["files"]:
            path = target / item["path"]
            if not path.is_file():
                problems.append(f"{package['run_id']}: 缺文件 {item['path']}")
            elif sha(path) != item["sha256"]:
                problems.append(f"{package['run_id']}: 哈希不符 {item['path']}")
        score = adjudicate(package["case_id"], target / "outputs")
        if score["legacy_artifact_result"]["objective_score"] != package["objective_score"]:
            problems.append(f"{package['run_id']}: 重算分数不一致")
        if score["accepted"] != package["accepted"]:
            problems.append(f"{package['run_id']}: accepted 不一致")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for problem in problems:
            print("FAIL", problem)
        print(f"week5-pilots: {'一致' if not problems else str(len(problems)) + ' 处问题'}")
        return 1 if problems else 0
    manifest = build_all()
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    for package in manifest["packages"]:
        print(package["run_id"], package["objective_score"], package["failed_checks"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
