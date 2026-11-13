"""结论快照门：结论文本、输入证据与哈希一起版本化，变动必须有差异记录。

    python -X utf8 scripts/verify_conclusion_snapshots.py --check
    python -X utf8 scripts/verify_conclusion_snapshots.py --record --reason "补记……"

背景（Issue #2 P1）：CL-01 的预期哈希曾随台账增长被静默改写，只靠人工在 pin_note
里补记。这个脚本把“冻结值”钉在 Git 对象上：结论文件任一字节变化，都必须先追加一条
带日期、理由、新哈希和证据清单的差异记录，否则 --check 直接失败。

检查四件事：
  1. 结论文件的当前 sha256 等于索引里最后一条差异记录。
  2. 该记录的证据清单（路径 + sha256）等于结论文件内嵌的 evidence。
  3. 记录里的 git blob 仍可取回，且内容哈希与记录一致（旧快照没有被历史重写）。
  4. 每条证据的当前哈希与记录不同时只作提示，不判失败——台账增长是合法的，
     但结论必须随之下一次记录才能继续通过第 1 条。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "ledger/conclusions/index.json"
CONCLUSIONS = ("CL-01", "CL-02", "CL-03", "CL-04")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def path_of(conclusion_id: str) -> Path:
    return ROOT / "ledger/conclusions" / f"{conclusion_id}.json"


def evidence_of(document: dict) -> list[dict]:
    return [{"path": item["path"], "sha256": item["sha256"]}
            for item in document.get("evidence", [])]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True)


def blob_of(path: Path, *, store: bool = False) -> str:
    args = ["hash-object"] + (["-w"] if store else []) + ["--", str(path.relative_to(ROOT))]
    result = git(*args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def blob_readable(blob: str) -> bytes | None:
    result = git("cat-file", "-p", blob)
    return result.stdout if result.returncode == 0 else None


def record(conclusion_id: str, reason: str) -> dict:
    path = path_of(conclusion_id)
    document = json.loads(path.read_text(encoding="utf-8"))
    return {
        "date": date.today().isoformat(),
        "reason": reason,
        "file_sha256": sha256_bytes(path.read_bytes()),
        "git_blob": blob_of(path, store=True),
        "pinned_at": document.get("pinned_at"),
        "evidence": evidence_of(document),
        "replayed_experiment_sha256":
            document.get("reproducible_experiment", {}).get("expected_output_sha256"),
    }


def load_index() -> dict:
    if not INDEX.is_file():
        return {"schema": "tx-harness/conclusion-snapshots/v1", "conclusions": {}}
    return json.loads(INDEX.read_text(encoding="utf-8"))


def save_index(index: dict) -> None:
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check() -> list[str]:
    problems = []
    index = load_index()
    for conclusion_id in CONCLUSIONS:
        path = path_of(conclusion_id)
        if not path.is_file():
            problems.append(f"{conclusion_id}: 缺结论文件")
            continue
        entry = index["conclusions"].get(conclusion_id)
        if not entry or not entry.get("history"):
            problems.append(f"{conclusion_id}: 索引里没有差异记录")
            continue
        latest = entry["history"][-1]
        actual = sha256_bytes(path.read_bytes())
        if actual != latest["file_sha256"]:
            problems.append(
                f"{conclusion_id}: 结论文本已变（记录 {latest['file_sha256'][:12]}…，"
                f"当前 {actual[:12]}…），但没有新增差异记录；"
                f"改完请跑 --record --reason \"...\"")
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if evidence_of(document) != latest["evidence"]:
            problems.append(f"{conclusion_id}: 索引证据清单与结论内嵌 evidence 不一致")
        blob = blob_readable(latest.get("git_blob", ""))
        if blob is None:
            problems.append(f"{conclusion_id}: 记录的 git blob 不可取回（快照丢失）")
        elif sha256_bytes(blob) != latest["file_sha256"]:
            problems.append(f"{conclusion_id}: git blob 内容与记录的哈希不符")
    return problems


def drift() -> list[str]:
    """证据文件相对快照的漂移提示；只在存在时打印，不判失败。"""
    notes = []
    index = load_index()
    for conclusion_id, entry in index["conclusions"].items():
        if not entry.get("history"):
            continue
        for item in entry["history"][-1]["evidence"]:
            path = ROOT / item["path"]
            if not path.is_file():
                notes.append(f"{conclusion_id}: 证据文件缺失 {item['path']}")
                continue
            actual = sha256_bytes(path.read_bytes())
            if actual != item["sha256"]:
                notes.append(f"{conclusion_id}: {item['path']} 已漂移"
                             f"（快照 {item['sha256'][:12]}… → 当前 {actual[:12]}…）")
    return notes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验（默认行为）")
    parser.add_argument("--record", action="store_true", help="记录当前状态为新的差异记录")
    parser.add_argument("--reason", default="", help="记录差异的原因，必须非空")
    parser.add_argument("--id", default="", help="只记录某一个结论")
    args = parser.parse_args(argv)

    if args.record:
        if not args.reason.strip():
            print("FAIL --record 必须带 --reason")
            return 1
        index = load_index()
        targets = [args.id] if args.id else list(CONCLUSIONS)
        for conclusion_id in targets:
            entry = index["conclusions"].setdefault(conclusion_id, {"history": []})
            entry["history"].append(record(conclusion_id, args.reason.strip()))
            entry["latest"] = entry["history"][-1]
        save_index(index)
        print(f"recorded: {', '.join(targets)}")
        return 0

    problems = check()
    for note in drift():
        print("NOTE", note)
    for problem in problems:
        print("FAIL", problem)
    print(f"conclusion-snapshots: {len(CONCLUSIONS)} 条结论，"
          f"{'0 处问题' if not problems else str(len(problems)) + ' 处问题'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
