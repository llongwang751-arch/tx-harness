"""Export reviewed native-desktop observations and untouched WorkBuddy T01 files.

UI control is performed with documented native CUA in node_repl. This script
only collects an already-completed isolated run and exports a narrow whitelist
of observed AX labels; private screenshots/AX and account/history stay private.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_eval.core import evaluate

RUN = "workbuddy-T01-desktop-r1"
SOURCE = ROOT / "private/pilots" / RUN
TARGET = ROOT / "public/pilots" / RUN
FILES = ("order_ledger.csv", "aggregate.json", "exceptions.json")
REVIEWED_CAPTURES = (
    "initial", "workspace-bound-recheck", "prompt-ready", "task-submitted",
    "task-created-recheck", "task-progress-1", "task-progress-2",
    "final-delivery-declaration-recheck",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reviewed_label(line):
    """Keep specific observable configuration/status/artifact labels only.

    This is deliberately not a general transcript exporter: it omits all
    planning/derivation text and all sidebar, account and document URL fields.
    """
    text = line.strip()
    exact = (
        r"\d+ 文本 5\.7\.7",
        r"\d+ 文本 pilot-workbuddy-T01-desktop-r1",
        r"\d+ 组合框 \(settable, string\) Select model: Deepseek-V4\.1-Flash Value: Deepseek-V4\.1-Flash",
        r"\d+ 组合框 \(settable, string\)(?: Value:)? 允许完全访问",
        r"\d+ 按钮 (?:\(disabled\) )?(?:发送|停止)",
        r"\d+ 文本 已处理 \d+s",
        r"\d+ 文本 修改、运行校验：order_ledger\.csv",
        r"\d+ 文本 Validate outputs with BOM handling",
        r"\d+ 文本 正在执行命令",
        r"\d+ 文本 三份文件已写入",
        r"\d+ 文本 outputs/",
        r"\d+ 文本 ，已完成解析与交叉校验。",
        r"\d+ (?:按钮|文本) (?:aggregate\.json|exceptions\.json|order_ledger\.csv)",
        r"\d+ 文本 (?:323|442|273) B",
        r"\d+ 按钮 查看所有产物 \(3\)",
        r"\d+ 文本 汇总",
        r"\d+ 文本 ：总计 4 单，gross 50300、refund 7000、net 43300；",
        r"\d+ 文本 business",
        r"\d+ 文本 2 单（26500/3000/23500）、",
        r"\d+ 文本 retail",
        r"\d+ 文本 2 单（23800/4000/19800），按组名升序。",
        r"\d+ 文本 异常",
        r"\d+ 文本 ：dup_order=1、superseded_order=1、dup_refund=1、superseded_refund=1；orphan=\[R007\]（O999 不在最新订单集）；non_success=\[R004\(failed\), R006\(pending\)\]；ineligible=\[R008\]（O103 已取消）。三类互不重叠。",
    )
    return text if any(re.fullmatch(pattern, text) for pattern in exact) else None


def main():
    if TARGET.exists():
        raise FileExistsError("Refuse overwrite or selective re-export of a published pilot")
    plan = read(SOURCE / "plan.json")
    workspace = Path(plan["workspace"]).resolve()
    participant_root = Path("D:/harness-participants").resolve()
    if workspace.parent != participant_root or workspace.name != "pilot-" + RUN:
        raise ValueError("Unexpected participant workspace")
    initial = read(SOURCE / "initial-inventory.json")
    unchanged = all((workspace / name).is_file() and digest(workspace / name) == expected
                    for name, expected in initial.items())
    if not unchanged:
        raise ValueError("Inputs/prompt changed: preserve privately and require new review")
    for name in FILES:
        path = (workspace / "outputs" / name).resolve()
        if not path.is_relative_to(workspace) or not path.is_file():
            raise ValueError("Required native file missing or escapes workspace")
    actual_outputs = {p.relative_to(workspace / "outputs").as_posix()
                      for p in (workspace / "outputs").rglob("*") if p.is_file()}
    if actual_outputs != set(FILES):
        raise ValueError("Unexpected outputs: manual privacy review required")
    captures = [json.loads(line) for line in (SOURCE / "capture-log.jsonl").read_text(encoding="utf-8").splitlines()]
    selected = {entry["label"]: entry for entry in captures if entry["label"] in REVIEWED_CAPTURES}
    if set(selected) != set(REVIEWED_CAPTURES):
        raise ValueError("Reviewed observations missing or renamed")
    events = []
    for label in REVIEWED_CAPTURES:
        entry = selected[label]
        path = SOURCE / entry["ax"]
        labels = [{"source_line": number, "text": kept}
                  for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                  if (kept := reviewed_label(line))]
        if not labels:
            raise ValueError("Reviewed capture has no matching public labels")
        events.append({"event_id": "ui-" + str(entry["index"]), "kind": "native_ui_observation",
                       "received_at": entry["at"], "phase": label, "labels": labels,
                       "private_ax_sha256": digest(path),
                       "collection_scope": "Reviewed AX excerpts; no exact tool-call arguments or complete runtime stream"})
    visible = json.dumps(events, ensure_ascii=False)
    if any(term in visible.lower() for term in ("accountsnapshot", "file://", "c:\\users", "uid", "nickname", "token", "cookie")):
        raise ValueError("Unexpected private field in public excerpts")
    completion = selected["task-progress-2"]
    completion_ax = (SOURCE / completion["ax"]).read_text(encoding="utf-8")
    if "按钮 (disabled) 发送" not in completion_ax or "按钮 查看所有产物 (3)" not in completion_ax:
        raise ValueError("Completion observation does not establish stopped processing and artifacts")
    start = read(SOURCE / "execution-start.json")
    start_at = datetime.fromisoformat(start["started_at"].replace("Z", "+00:00"))
    completed_at = datetime.fromisoformat(completion["at"].replace("Z", "+00:00"))
    elapsed = (completed_at - start_at).total_seconds()
    if not 0 < elapsed <= 1200:
        raise ValueError("Completion outside pilot time limit")
    verification = evaluate(ROOT / "cases/T01", workspace / "outputs")
    TARGET.mkdir(parents=True)
    shutil.copyfile(workspace / "prompt.md", TARGET / "prompt.md")
    shutil.copytree(workspace / "inputs", TARGET / "inputs")
    shutil.copyfile(SOURCE / "submitted-prompt.txt", TARGET / "submitted-prompt.txt")
    shutil.copytree(workspace / "outputs", TARGET / "outputs")
    save(TARGET / "verification.json", verification)
    with (TARGET / "visible-events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    metadata = {
        "run_id": RUN, "product_id": "workbuddy", "case_id": "T01", "track": "pilot",
        "stage": "native_desktop_task_pilot", "formal_sample": False, "formal_eligible": False,
        "surface": "WorkBuddy 5.7.7 native desktop new task via documented native CUA",
        "version_visible": "5.7.7", "model_visible": plan["model_visible"],
        "model_selector_changed": False, "underlying_model_version": None,
        "account_edition": "free", "permission_visible": plan["permission_visible"],
        "permission_changed": False, "explicit_user_skill_selected": False,
        "active_skills": None, "skills_disabled_verified": False, "mcp_hooks_state": None,
        "requested_no_network": True, "network_absence_independently_verified": False,
        "os_sandbox_verified": False, "workspace_scope": "Fresh external participant directory; prompt, two CSV inputs, initially empty outputs; no oracle",
        "started_at": start["started_at"], "completion_observed_at": completion["at"],
        "elapsed_to_completion_observation_seconds": elapsed,
        "timing_basis": "Collector timestamp immediately before native send action to first captured visible completion; service finish time and CPU/tool timing unknown",
        "timeout_seconds": 1200, "timed_out": False, "followup_prompts": [],
        "source_prompt_sha256": digest(TARGET / "prompt.md"),
        "submitted_prompt_sha256": digest(TARGET / "submitted-prompt.txt"),
        "prompt_adapter_appendix": plan["prompt_adapter_appendix"],
        "prompt_transport": "CUA native paste text followed by native send; editor AX normalizes visual whitespace, exact internal model-request bytes unavailable",
        "initial_inventory": initial, "inputs_unchanged": unchanged,
        "product_deliverables": {name: {"sha256": digest(TARGET / "outputs" / name),
                                       "bytes": (TARGET / "outputs" / name).stat().st_size} for name in FILES},
        "output_repairs_by_evaluator": False, "objective_score": verification["objective_score"],
        "manual_score": None, "total_score": None, "pure_harness_score": None,
        "actual_tool_calls": None, "visible_operation_labels": ["修改、运行校验：order_ledger.csv", "Validate outputs with BOM handling", "正在执行命令"],
        "collector_preflight_issues": ["Folder-dialog AX elements were unavailable in cached native state; screenshot exposed multiple regions. Documented screenshot with caught exception preserved the displayed regions, then native coordinate confirmation selected the verified isolated directory. All before task submission."],
        "confidence": "high for published original-file correctness and observed UI labels; limited for internal execution and model/Skill/Harness attribution",
        "attribution": "End-to-end result under recorded configuration; no isolated Harness causal score",
        "redaction": "Exact reviewed AX-label whitelist only. Account URL/snapshot, identity, other projects/history, raw screenshots, all planning/derivation text, system prompts and authentication fields omitted. Raw observations remain private; no native tool stream was extracted.",
        "checker_snapshot": {name: digest(ROOT / name) for name in ("harness_eval/core.py", "cases/T01/case.json", "cases/T01/oracle.json", "scripts/export_workbuddy_desktop_pilot.py")},
    }
    save(TARGET / "metadata.json", metadata)
    (TARGET / "verification.md").write_text(
        "# WorkBuddy T01 原生桌面预试\n\n"
        "真实登录的 WorkBuddy 5.7.7 新任务，模型选择器为 Deepseek-V4.1-Flash、权限为允许完全访问、账户edition为free。"
        "模型及权限没有由评测者更改；没有手动选择用户Skill，内置及其他生效Skill不可由本次确认。\n\n"
        "起始隔离目录仅有题目、两份CSV及空outputs。提交原始题目后只追加共同交付说明，未发送追问。"
        "原生界面先显示处理中，随后显示校验操作标签，最终声明三份文件已写入并展示三个产物卡片。"
        "公开可见记录是代理/操作人审阅后的AX标签摘录，不是完整工具流；所有规划/推导文本和私有侧栏被省略。\n\n"
        "三份原始文件通过8/8确定性检查，客观分60/60。CSV保留产品原生UTF-8 BOM（323字节），"
        "JSON分别为442、273字节。评测者没有去BOM、修改输出或提供oracle；输入和题目哈希均未变。\n\n"
        f"从发送动作前时间戳到首次采集到完成界面为{elapsed:.3f}秒；这是观察区间上界，服务完成时刻不可见。"
        "不用于不同模型、入口或采样条件的速度排名。\n\n"
        "这是一次探索性episode，不计正式样本。正确交付仅支持这一配置的端到端结果；"
        "模型路由、Skill内容、真实执行参数及网络使用不可完全复核，因此manual、总分、纯Harness分保持null。"
        "此前两次独立CLI认证诊断完整保留，不能用本次桌面成功覆盖它们。\n\n"
        "复核：`python -X utf8 -m harness_eval verify --case T01 --outputs public/pilots/workbuddy-T01-desktop-r1/outputs`。"
        "manifest覆盖所有公开文件；哈希完整性不单独证明记录来源真实性。\n",
        encoding="utf-8")
    save(TARGET / "manifest.json", {p.relative_to(TARGET).as_posix(): digest(p)
                                   for p in sorted(TARGET.rglob("*")) if p.is_file()})
    print(json.dumps({"exported": RUN, "visible_observations": len(events),
                      "checks_passed": sum(c["passed"] for c in verification["checks"]),
                      "checks_total": len(verification["checks"]),
                      "objective_score": verification["objective_score"],
                      "elapsed_observation_seconds": elapsed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
