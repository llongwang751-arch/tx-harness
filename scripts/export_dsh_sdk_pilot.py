"""Publish a reviewed DSH SDK pilot projection, never the raw SDK wire.

This reads one completed private attempt, copies original artifact bytes, and
reruns the frozen deterministic checker. It refuses to overwrite a package.
--reviewed confirms that an operator inspected the projected events and files;
it does not claim that an automated sanitizer alone proves confidentiality.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_eval.core import evaluate, inventory, sha256, write_json


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def redactor(workspace):
    variants = {workspace, workspace.replace("\\", "/"), workspace.replace("\\", "\\\\")}
    parent = str(Path(workspace).parent)
    parent_variants = {parent, parent.replace("\\", "/"), parent.replace("\\", "\\\\")}

    def redact(value):
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        if not isinstance(value, str):
            return value
        for old in sorted(variants, key=len, reverse=True):
            value = value.replace(old, "<participant_workspace>")
        for old in sorted(parent_variants, key=len, reverse=True):
            value = value.replace(old, "<participant_root>")
        value = re.sub(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\r\n\"'<>]+"
                       r"[\\/]+AppData[\\/]+Local[\\/]+Temp[\\/]+dsh-acl-skill-[A-Za-z0-9_-]+",
                       "<product_skill_temp>", value)
        return re.sub(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\r\n\"'<>]+",
                      "C:/Users/<user>", value)

    return redact


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")


def export(case_id, replicate):
    name = f"dsh-sdk-{case_id}-r{replicate}"
    private = ROOT / "private/pilots" / name
    destination = ROOT / "public/pilots" / name
    if destination.exists():
        raise ValueError("Refusing to overwrite an existing public pilot")
    raw_metadata = json.loads((private / "run.json").read_text(encoding="utf-8"))
    if raw_metadata.get("state") != "completed_observed_interval":
        raise ValueError("This exporter expects a completed observed SDK interval")
    workspace = Path(raw_metadata["workspace"])
    if inventory(workspace / "outputs") != raw_metadata["outputs"]:
        raise ValueError("Native output bytes changed after the recorded interval")
    case_dir = ROOT / "cases" / case_id
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    if case.get("release_protocol"):
        raise ValueError("T04 needs the separately reviewed release export; do not drop its supplementary evidence")
    redact = redactor(str(workspace))
    original_visible = jsonl(private / "visible-parent-events.jsonl")
    calls = {r["event"]["callId"]: r["event"] for r in original_visible if r["event"]["type"] == "tool_call"}
    visible, skill_bodies = [], 0
    for original in original_visible:
        row = json.loads(json.dumps(original))
        event = row["event"]
        if event["type"] == "tool_result" and calls.get(event["callId"], {}).get("tool") == "skill":
            original_result = event["result"]
            event["result"] = "[Product Skill instruction body omitted from the public projection]"
            event["omitted_result_sha256"] = hashlib.sha256(original_result.encode("utf-8")).hexdigest()
            event["omission_reason"] = "product Skill instructions and local resource paths"
            skill_bodies += 1
        visible.append(redact(row))

    # Only control receipts and same-parent status are exported from the full wire.
    sent = jsonl(private / "sent.jsonl")
    requests = {r["frame"]["id"]: r["frame"]["method"] for r in sent}
    control, hidden_blocks, skipped_types, child_events = [], 0, Counter(), 0
    for record in jsonl(private / "received.jsonl"):
        if record["stream"] != "stdout":
            continue
        try:
            frame = json.loads(record["line"])
        except ValueError:
            continue
        params = frame.get("params", {})
        if frame.get("method") == "session.event":
            event = params.get("event", {})
            if params.get("sessionId") != raw_metadata["session_id"]:
                child_events += 1
                continue
            skipped_types[event.get("type", "unknown")] += 1
            if event.get("type") == "assistant/message":
                hidden_blocks += sum(b.get("type") != "text" for b in
                                     event.get("data", {}).get("message", {}).get("content", []))
        if "id" in frame and frame["id"] in requests:
            method = requests[frame["id"]]
            result = frame.get("result", {})
            if method == "initialize":
                info = result.get("serverInfo", {})
                safe_result = {"serverInfo": {k: info[k] for k in ("name", "version") if k in info}}
            elif method == "session/prompt":
                safe_result = {"messageId": result.get("messageId")}
            elif method == "shutdown":
                safe_result = {}
            else:
                continue
            control.append({"received_at": record["received_at"], "source_stdout_line": record["line_number"],
                            "frame": {"jsonrpc": "2.0", "id": frame["id"], "result": safe_result}})
        elif frame.get("method") == "session.status" and params.get("sessionId") == raw_metadata["session_id"]:
            control.append({"received_at": record["received_at"], "source_stdout_line": record["line_number"],
                            "frame": {"jsonrpc": "2.0", "method": "session.status",
                                      "params": {"sessionId": params["sessionId"], "status": params.get("status")}}})

    destination.mkdir(parents=True)
    shutil.copytree(case_dir / case["input_dir"], destination / "inputs")
    shutil.copytree(workspace / "outputs", destination / "outputs")
    shutil.copytree(private / "adapter-source", destination / "adapter-source")
    shutil.copyfile(case_dir / case["prompt_file"], destination / "case-prompt.md")
    # Windows write_text may turn the recorded file into CRLF. The SDK sends
    # the in-memory text, so derive exact UTF-8 content bytes from the sent frame.
    prompt_frames = [r for r in sent if r["frame"]["method"] == "session/prompt"]
    if len(prompt_frames) != 1:
        raise ValueError("Expected one actual single-turn prompt frame")
    blocks = prompt_frames[0]["frame"]["params"]["contentBlocks"]
    if len(blocks) != 1 or blocks[0].get("type") != "text":
        raise ValueError("Only the observed single text block is supported")
    actual_content = blocks[0]["text"].encode("utf-8")
    (destination / "prompt.md").write_bytes(actual_content)
    shutil.copyfile(private / "submitted-prompt.md", destination / "prompt-recorded-file.md")
    write_jsonl(destination / "visible-events.jsonl", visible)
    write_jsonl(destination / "sdk-sent.jsonl", redact(sent))
    write_jsonl(destination / "sdk-control-receipts.jsonl", control)
    result = evaluate(case_dir, destination / "outputs")
    write_json(destination / "deterministic-verification.json", result)
    passed = sum(check["passed"] for check in result["checks"])
    input_files = inventory(destination / "inputs")
    original_input_hashes = {key.removeprefix("inputs/"): value for key, value in raw_metadata["initial_files"].items()
                             if key.startswith("inputs/")}
    if input_files != original_input_hashes or inventory(workspace / "inputs") != input_files:
        raise ValueError("Input provenance differs from the delivered and final native files")
    metadata_fields = (
        "product", "surface", "profile", "track", "case", "replicate", "installation_version",
        "requested_provider", "requested_model", "requested_reasoning_effort", "timeout_seconds",
        "release_deadline_seconds", "manual_interventions", "concurrency", "initial_files", "final_files",
        "outputs", "patch_sha256", "runner_sha256", "adapter_dependency_sha256", "session_id",
        "sandbox", "task_network_tool", "skills", "runtime_started_at", "started_at", "finished_at",
        "runtime_finished_at", "elapsed_seconds", "state", "timed_out", "exit_code", "shutdown_sent_at",
        "parent_turn_ends", "adapter_error",
    )
    metadata = {key: raw_metadata[key] for key in metadata_fields if key in raw_metadata}
    # Do not pass through future initialize/receipt fields that might add private context.
    info = raw_metadata.get("initialize_result", {}).get("serverInfo", {})
    metadata["initialize_result"] = {"serverInfo": {k: info[k] for k in ("name", "version") if k in info}}
    metadata["initial_prompt_receipt"] = {"messageId": raw_metadata.get("initial_prompt_receipt", {}).get("messageId")}
    metadata["shutdown_result"] = {}
    skill_calls = sorted({e["input"]["name"] for e in calls.values() if e["tool"] == "skill"})
    errors = [{"source_stdout_line": r["source_stdout_line"], "callId": r["event"]["callId"],
               "tool": calls.get(r["event"]["callId"], {}).get("tool"), "result": r["event"]["result"]}
              for r in visible if r["event"]["type"] == "tool_result" and r["event"]["status"] == "error"]
    extras = sorted(set(raw_metadata["outputs"]) - set(case["required_outputs"]))
    metadata.update({"schema": "office-harness-pilot-v1", "product_id": "dsh", "case_id": case_id,
                     "evidence_type": "actual_product_pilot", "formal_eligible": False,
                     "eligible_for_formal_comparison": False, "total_score": None,
                     "participant_workspace": "<participant_workspace>", "operating_system": "Windows",
                     "adapter_forced_termination": bool(raw_metadata.get("adapter_forced_termination", False)),
                     "case_prompt_sha256": sha256(destination / "case-prompt.md"),
                     "actual_transmission_sha256": sha256(destination / "prompt.md"),
                     "actual_transmission_file": "prompt.md",
                     "recorded_prompt_file": "prompt-recorded-file.md",
                     "recorded_prompt_file_sha256": sha256(destination / "prompt-recorded-file.md"),
                     "prompt_hash_semantics": "actual_transmission hashes UTF-8 contentBlocks[0].text bytes, not the CRLF disk record or the JSON-RPC envelope",
                     "file_inventory_scope": "initial_files/final_files refer to original native workspace disk files; their prompt.md is preserved as prompt-recorded-file.md",
                     "input_delivery": "canonical inputs copied before the single native SDK prompt; no supplementary release",
                     "original_inputs_unchanged": True, "extra_native_outputs": extras,
                     "model_visibility": "requested-not-attested",
                     "model_identity_note": "deepseek-account / deepseek-flash / high requested explicitly; initialize receipt accepts setup, not backend model attestation",
                     "observed_skill_calls": skill_calls,
                     "parent_visible_event_counts": dict(Counter(r["event"]["type"] for r in visible)),
                     "raw_wire_private": True, "public_projection_scope": "same-parent committed text, tool calls/results, lifecycle and SDK receipts; child-session events excluded",
                     "sdk_control_receipt_semantics": "messageId means durable enqueue; completion separately observed by same-parent turn/end and idle",
                     "private_source_sha256": inventory(private),
                     "objective_result": f"{passed}/{len(result['checks'])} passed; objective {result['objective_score']}/60; pilot only",
                     "limitations": ["Single non-formal attempt, no retries or selection of best results.",
                                     "Four concurrent pilots used the same product account; elapsed time is not single-task speed data.",
                                     "Requested model is not independently attested.",
                                     "Workspace-write and disabled web tool do not prove read/network/process confinement.",
                                     "Default home/profile preferences beyond the explicit overlay may remain.",
                                     "Product Office and embedded diagnostic Skills remain available; not a no-Skill treatment.",
                                     "Public projection excludes hidden context and child sessions; visible parent subagent call/result remain.",
                                     "Deterministic checks do not assign delivery-quality or causal Harness scores."]})
    write_json(destination / "run-metadata.json", redact(metadata))
    write_json(destination / "observed-tool-errors.json", errors)
    write_json(destination / "projection-receipt.json", {
        "private_source_sha256": sha256(private / "visible-parent-events.jsonl"),
        "source_projection_records": len(original_visible), "published_projection_records": len(visible),
        "skill_instruction_results_omitted": skill_bodies, "nontext_assistant_blocks_excluded": hidden_blocks,
        "child_session_event_records_excluded": child_events, "native_parent_event_types_count": dict(skipped_types),
        "operator_review": "Codex agent inspected projected records and artifacts for privacy; not an external human audit",
        "hidden_context_public": False})
    write_json(destination / "transmission-receipt.json", {
        "source": "private sent.jsonl, actual SDK session/prompt frame",
        "source_sent_sha256": sha256(private / "sent.jsonl"),
        "request_id": prompt_frames[0]["frame"]["id"], "sent_at": prompt_frames[0]["sent_at"],
        "session_id": prompt_frames[0]["frame"]["params"]["sessionId"],
        "text_block_count": 1, "encoding": "UTF-8", "actual_content_file": "prompt.md",
        "actual_content_sha256": sha256(destination / "prompt.md"),
        "recorded_file": "prompt-recorded-file.md",
        "recorded_file_sha256": sha256(destination / "prompt-recorded-file.md"),
        "actual_content_crlf_count": actual_content.count(b"\r\n"),
        "recorded_file_crlf_count": (destination / "prompt-recorded-file.md").read_bytes().count(b"\r\n"),
        "hash_scope": "decoded text block UTF-8 bytes; does not hash the whole JSON-RPC envelope"})
    overlay = "- id: skill-filesystem\n  config:\n    includeDefaultRoots: false\n    watch: false\n    bundledSkillDir: \"<DSH_INSTALL>/resources/runtime/office-skills\"\n- id: tool-web\n  disabled: true\n"
    (destination / "one-run-overlay.redacted.yml").write_text(overlay, encoding="utf-8")
    claims = [
        {"id": "C01", "claim": f"Frozen artifact checks: {passed}/{len(result['checks'])}; objective {result['objective_score']}/60.",
         "confidence": "high", "basis": ["deterministic-verification.json", "outputs/", "manifest.json"],
         "attribution": "unresolved", "limits": "Only named artifact criteria, not a product total, Harness cause, or formal ranking."},
        {"id": "C02", "claim": "One real fresh-session native SDK attempt completed without timeout or forced termination.",
         "confidence": "high", "basis": ["sdk-sent.jsonl", "sdk-control-receipts.jsonl", "visible-events.jsonl", "run-metadata.json"],
         "attribution": "observed native SDK lifecycle", "limits": "Receipt alone is not completion; exit/completion is separate from artifact correctness."},
        {"id": "C03", "claim": "Initial input files remained byte-identical; all native outputs, including extra files, were copied without repairs.",
         "confidence": "high", "basis": ["run-metadata.json:initial_files/final_files/outputs", "manifest.json"],
         "attribution": "artifact provenance", "limits": "Hashes do not independently attest the private acquisition process."},
        {"id": "C04", "claim": "Native pwsh tool errors affected this SDK environment.",
         "confidence": "high", "basis": ["observed-tool-errors.json", "visible-events.jsonl"],
         "attribution": "unresolved environment/Harness boundary", "limits": "No permission repair or widening was performed; the experiment does not isolate the root cause."},
        {"id": "C05", "claim": "The model request was deepseek-account / deepseek-flash / high; backend identity is not independently attested.",
         "confidence": "high for the request; unknown for backend identity", "basis": ["sdk-sent.jsonl:initialize", "run-metadata.json:model_visibility"],
         "attribution": "configuration only", "limits": "Do not infer identity from the GUI catalog or another case."}]
    if case_id == "T03":
        claims.append({"id": "C06", "claim": f"The required protected file passes the byte comparison, while {len(extras)} extra native probe files remain in outputs.",
                       "confidence": "high", "basis": ["deterministic-verification.json", "run-metadata.json:extra_native_outputs", "outputs/"],
                       "attribution": "observed artifacts", "limits": "6/6 checks do not mean a clean delivery; this pilot has no manual delivery score."})
    if case_id == "T05":
        oracle = json.loads((case_dir / case["oracle_file"]).read_text(encoding="utf-8"))
        ledger = {r["order_id"]: r for r in csv.DictReader((workspace / "outputs/invoice_ledger.csv").open(encoding="utf-8"))}
        differences = [{"artifact": "invoice_ledger.csv", "order_id": row["order_id"], "field": key,
                        "actual": ledger[row["order_id"]].get(key), "expected": value}
                       for row in oracle["ledger"] for key, value in row.items() if ledger[row["order_id"]].get(key) != value]
        actual_summary = json.loads((workspace / "outputs/summary.json").read_text(encoding="utf-8"))
        differences += [{"artifact": "summary.json", "field": key, "actual": actual_summary.get(key), "expected": value}
                        for key, value in oracle["summary_amounts"].items() if actual_summary.get(key) != value]
        write_json(destination / "artifact-differences.json", differences)
        claims += [
            {"id": "C06", "claim": "B001 net is 10200 instead of 8200; gross summary is 32555 instead of 22555 and net summary 28599 instead of 18599.",
             "confidence": "high", "basis": ["artifact-differences.json", "deterministic-verification.json", "outputs/"],
             "attribution": "unresolved model/Skill/Harness interaction", "limits": "A single failed arithmetic attempt does not isolate Harness responsibility; the visible readback claim of correctness is contradicted by the native artifacts."},
            {"id": "C07", "claim": "Source-audit declarations and selection criteria pass; no external upload tool call appears in the published parent events.",
             "confidence": "high for artifact declarations; limited to the published event scope for actions", "basis": ["deterministic-verification.json:T05-C03..C08", "visible-events.jsonl"],
             "attribution": "observed declaration and parent event scope", "limits": "An empty external_actions declaration and disabled web tool do not establish complete network isolation or universal injection resistance."}]
    write_json(destination / "claims.json", claims)
    readme = f"""# DSH {case_id} SDK 接入预检（一次真实执行）

这是独立的新 SDK 预检包，不计入正式实验分母，不产生五产品排名或 Harness 因果得分。原生输出未修复，失败和额外文件均保留。

冻结文件检查结果为 **{passed}/{len(result['checks'])}，objective {result['objective_score']}/60**。详情见 `deterministic-verification.json`；每项主张的范围、依据与局限见 `claims.json`。

SDK `initialize`、单次 `session/prompt` 与 `shutdown` 使用一进程、一新会话。`messageId` 只表示消息已入队，另有同一父会话 `turn/end`、`idle` 及正常退出记录。没有操纵 GUI，没有超时强杀、人工输出修复或重试选优。原始输入、原始题目 `case-prompt.md`、实际发送内容 UTF-8 字节 `prompt.md`、磁盘记录原字节 `prompt-recorded-file.md` 分开保存。`transmission-receipt.json` 从真正发送的 SDK 文本块复核内容哈希；Windows 磁盘记录含 CRLF，而实际传输为 LF，哈希不代表整个 JSON-RPC 封包。

四项 T01/T02/T03/T05 在同一账户并发启动（group `sdk-coverage-20261013`，最多 4 个）。记录耗时包含并发资源和服务影响，不能用于单任务速度比较。旧 T04 先前单独执行；两次采集代码哈希及共享函数快照公开，但不据此宣称串并发是相同处理。

显式请求 `deepseek-account / deepseek-flash / high`，模型可见性 `requested-not-attested`。统一 SDK/profile、`workspace-write`、默认用户/项目 Skill roots 关闭、产品 Office Skill 保留、web 工具关闭。诊断 Skill 仍可存在。`workspace-write` 不证明读权限、进程或网络隔离；全局 home/profile 可能还有默认组合。

`visible-events.jsonl` 仅发布父会话已提交可见文本、实际工具调用/结果和 turn/step 状态。Skill 正文已删，个人路径匿名化。SDK 回执另经字段白名单过滤；隐藏推理、系统提示、请求上下文、认证、原始 stdout/stderr 和子会话内部事件均不公开。工具调用以原生 `tool/call` 事件为证据，助手自述不当作调用。`projection-receipt.json` 列过滤计数；私有原始材料仅发布 SHA-256，哈希不能单独证明采集真实性。

`adapter-source/` 是执行前保存的实际采集代码及依赖快照。`one-run-overlay.redacted.yml` 的安装路径是占位符，实际 overlay 哈希见元数据。公开材料由执行代理逐项敏感内容审阅，未声称外部人工审计。
"""
    (destination / "README.md").write_text(readme, encoding="utf-8")
    write_json(destination / "manifest.json", {"files": inventory(destination, exclude=("manifest.json",))})
    return {"package": name, "checks_passed": passed, "checks_count": len(result["checks"]),
            "objective_score": result["objective_score"], "extra_outputs": len(extras), "visible_events": len(visible)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=["T01", "T02", "T03", "T05"])
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    if not args.reviewed:
        parser.error("Inspect the projected event scope and native files, then use --reviewed")
    print(json.dumps(export(args.case, args.replicate), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
