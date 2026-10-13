"""Publish only reviewed ordinary authentication-error evidence from WB pilots.

This deliberately does not export raw system events or arbitrary model messages.
The error string is checked exactly before export; all raw streams stay private.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
AUTH_ERROR = "Authentication required. Please use /login command to sign in to your account"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export(replicate, recover_incomplete=False):
    run_id = f"workbuddy-T01-r{replicate}"
    source = ROOT / "private/pilots" / run_id
    target = ROOT / "public/pilots" / run_id
    if target.exists() and not recover_incomplete:
        raise FileExistsError(f"Refuse overwrite: {target}")
    plan = json.loads((source / "plan.json").read_text(encoding="utf-8"))
    setting_sources = plan.get("setting_sources_requested")
    if setting_sources is None:
        flag_index = plan["command"].index("--setting-sources")
        setting_sources = plan["command"][flag_index + 1]
    result = json.loads((source / "result.json").read_text(encoding="utf-8"))
    initial = json.loads((source / "initial-inventory.json").read_text(encoding="utf-8"))
    workspace = Path(plan["participant_workspace"])
    if result["collected"] or not result["inputs_and_prompt_unchanged"]:
        raise ValueError("This narrow exporter handles only unchanged-input authentication failures")
    for name, expected in initial.items():
        if digest(workspace / name) != expected:
            raise ValueError(f"Initial file changed: {name}")
    if target.exists():
        allowed = set(initial) | {"submitted-prompt.txt", "outputs/README.md"}
        found = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        if not found.issubset(allowed) or any(digest(target / name) != value for name, value in initial.items()
                                            if (target / name).exists()):
            raise ValueError("Cannot recover completed, modified or unrecognized public directory")
        submitted = target / "submitted-prompt.txt"
        if submitted.exists() and digest(submitted) != digest(source / "submitted-prompt.txt"):
            raise ValueError("Cannot recover changed submitted prompt")
    events = []
    for line in (source / "stdout.raw").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("type") == "assistant":
            text = [block.get("text") for block in event.get("message", {}).get("content", [])
                    if block.get("type") == "text"]
            if text != [AUTH_ERROR]:
                raise ValueError("Unexpected ordinary message: require new manual privacy review")
            events.append({"event_id": "visible-message-1", "kind": "assistant_text", "text": AUTH_ERROR})
        elif event.get("type") == "result":
            if event.get("errors") != [AUTH_ERROR] or event.get("is_error") is not True:
                raise ValueError("Unexpected result: require new review")
            events.append({"event_id": "visible-result-1", "kind": "native_result",
                           "subtype": event["subtype"], "is_error": True, "errors": [AUTH_ERROR],
                           "duration_ms": event.get("duration_ms"), "num_turns": event.get("num_turns")})
    if len(events) != 2:
        raise ValueError("Need both actual ordinary message and error result")
    target.mkdir(parents=True, exist_ok=recover_incomplete)
    shutil.copyfile(workspace / "prompt.md", target / "prompt.md")
    shutil.copytree(workspace / "inputs", target / "inputs", dirs_exist_ok=recover_incomplete)
    shutil.copyfile(source / "submitted-prompt.txt", target / "submitted-prompt.txt")
    (target / "outputs").mkdir(exist_ok=recover_incomplete)
    (target / "outputs/README.md").write_text("此目录为缺失产物的说明。产品没有生成任何交付文件；本文件由评测者添加，不是产品产物。\n", encoding="utf-8")
    versions = json.loads((source / "versions.json").read_text(encoding="utf-8"))
    metadata = {
        "run_id": run_id, "product_id": "workbuddy", "case_id": "T01",
        "stage": "entrypoint_diagnostic_pilot", "formal_sample": False,
        "surface": "WorkBuddy 5.7.7 installed embedded CLI/headless",
        "versions": versions, "model_requested": None, "model_visible": "auto", "underlying_model": None,
        "settings_sources_requested": setting_sources,
        "requested_file_tools": ["Read", "Write", "Edit", "Glob", "Grep"],
        "tool_restriction_verified": False, "permission_mode_requested": "acceptEdits",
        "mcp_policy_requested": "strict empty MCP", "hooks_disable_requested": True,
        "skills_disabled_verified": False, "os_sandbox_verified": False,
        "source_prompt_sha256": digest(target / "prompt.md"),
        "submitted_prompt_sha256": digest(target / "submitted-prompt.txt"),
        "prompt_adapter_appendix": plan["prompt_adapter_appendix"],
        "initial_inventory": initial, "started_at": result["started_at"],
        "finished_at": result["finished_at"], "elapsed_seconds": result["elapsed_seconds"],
        "process_exit_code": result["exit_code"], "timed_out": result["timed_out"],
        "actual_tool_calls": [], "product_deliverables": [], "inputs_unchanged": True,
        "task_score": None, "failure_scope": "headless authentication before task execution",
        "attribution": "entrypoint/access condition; Harness task performance unresolved",
        "confidence": "high for observed authentication error only",
        "confidence_basis": ["visible-message-1", "visible-result-1"],
        "alternative_explanations": ["Desktop login may be separate from embedded CLI login",
                                     "Host-provided authentication route may be absent in standalone CLI"],
        "private_stdout_sha256": digest(source / "stdout.raw"),
        "redaction": "Only exact reviewed ordinary authentication text and native result fields retained. System, thinking, identifiers, authentication fields and absolute user paths omitted.",
    }
    save(target / "metadata.json", metadata)
    with (target / "visible-events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    (target / "verification.md").write_text(
        "# WorkBuddy T01 入口诊断预试\n\n"
        "这是实际安装 CLI 的一次独立执行记录，不计正式样本。未读认证值、未修复产品输出。\n\n"
        "普通回答与原生结果都要求 `/login`，且结果标记 `is_error=true`。没有工具调用和产品交付文件。"
        "退出码为0不能证明任务成功；本次任务得分留空。\n\n"
        "只允许的结论：当前独立 headless 入口未获得可用认证。"
        "置信依据为保存的普通消息与结果事件。桌面登录状态、实际底模、Skills 和任务执行能力无法由本次证明。\n\n"
        "`manifest.json` 可复核包内文件SHA256；`metadata.json` 记录原始与实际prompt哈希、输入哈希及实际UTC起止时间。"
        "原始流保存在本地private目录；公开流已去除系统事件、隐藏推理、认证字段、用户路径及会话标识。\n\n"
        "复现：安装相同版本后运行 `python scripts/run_workbuddy_pilot.py --case T01 --replicate <fresh-number>"
        f" --setting-sources {setting_sources} --execute`。认证状态可能不同，不能保证同样报错。\n",
        encoding="utf-8")
    manifest = {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob("*")) if p.is_file()}
    save(target / "manifest.json", manifest)
    print(f"Exported reviewed auth-error pilot: {run_id}; {len(manifest)} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recover-incomplete", action="store_true")
    options = parser.parse_args()
    for replicate in (1, 2):
        export(replicate, options.recover_incomplete)
