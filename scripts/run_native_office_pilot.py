"""Prepare/export reviewed native Yuanbao/Doubao pilots; never controls the UI.

Prepare copies canonical bytes only. Export consumes actual observations and
native download receipts; it does not generate or repair participant outputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_eval.core import evaluate, inventory

CASE_IDS = ("T01", "T02", "T03", "T04", "T05")
APPENDIX = "将交付文件写入 outputs/，不要修改 inputs/。"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def locations(product, case, attempt=1):
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        raise ValueError("Attempt must be a positive integer")
    name = f"{product}-{case}-desktop-r{attempt}"
    return name, Path("D:/harness-participants") / ("pilot-" + name), ROOT / "private/pilots" / name, ROOT / "public/pilots" / name


def prepare(product, case, attempt=1):
    name, workspace, private, _ = locations(product, case, attempt)
    if workspace.exists() or private.exists():
        raise FileExistsError("Refuse overwrite or retry; preserve the previous attempt")
    source = ROOT / "cases" / case
    files = [source / "prompt.md"] + sorted(p for p in (source / "inputs").rglob("*") if p.is_file())
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError("Input path escapes the canonical case")
    workspace.mkdir(parents=True)
    private.mkdir(parents=True)
    for path in files:
        target = workspace / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (workspace / "outputs").mkdir()
    prompt = (workspace / "prompt.md").read_bytes().decode("utf-8") + "\n" + APPENDIX + "\n"
    (private / "submitted-prompt.txt").write_bytes(prompt.encode("utf-8"))
    (private / "native-downloads").mkdir()
    snapshots = private / "prepare-source"
    snapshots.mkdir()
    shutil.copyfile(__file__, snapshots / Path(__file__).name)
    initial = inventory(workspace)
    save(private / "initial-inventory.json", initial)
    held = None
    if case == "T04":
        protocol = read(source / "case.json")["release_protocol"]
        if sorted(initial) != sorted(protocol["initial_delivery"]):
            raise ValueError("T04 initial workspace must contain only prompt and trades")
        release_folder = private / "held-release"
        release_folder.mkdir()
        shutil.copyfile(source / "releases/rates.json", release_folder / "rates.json")
        (private / "supplement-prompt.txt").write_bytes(protocol["response_text"].encode("utf-8"))
        held = {"private_file": "held-release/rates.json", "sha256": sha(release_folder / "rates.json"),
                "logical_target": "inputs/rates.json", "release_protocol": protocol,
                "not_initially_provided": True, "actual_remote_upload_available_at": None}
    mapping = [{"logical_path": p.relative_to(source).as_posix(), "original_attachment_name": p.name,
                "actual_attachment_name": None, "actual_server_path": None, "upload_verified": False}
               for p in files if p != source / "prompt.md"]
    save(private / "plan.json", {
        "schema": "native-office-pilot-preparation-v1", "run_id": name, "product_id": product,
        "case_id": case, "attempt": attempt, "prepared_at": now(), "workspace": str(workspace),
        "product_submission_performed": False, "formal_eligible": False, "formal_sample": False,
        "surface": "native_desktop_pending_execution", "mode_visible": "unknown_pending_capture",
        "version_visible": "unknown_pending_capture", "model_visible": "unknown_pending_capture",
        "source_prompt_sha256": sha(workspace / "prompt.md"),
        "submitted_prompt_sha256": sha(private / "submitted-prompt.txt"),
        "prompt_adapter_appendix": APPENDIX, "timeout_seconds": 1200,
        "initial_inventory": initial, "outputs_initially_empty": True,
        "attachment_path_mapping": mapping, "held_release": held,
        "prepare_source_sha256": inventory(snapshots),
        "source_protocol_sha256": sha(ROOT / "config/protocol.json"),
        "source_case_spec_sha256": sha(source / "case.json"),
        "note": "Preparation is not product evidence. Native UI mode/version, accepted uploads and native downloads must be recorded later. rN identifies a preserved pilot attempt, not a formal replicate.",
    })
    print(json.dumps({"prepared": name, "attempt": attempt, "workspace": str(workspace), "private": str(private),
                      "submitted_prompt": str(private / "submitted-prompt.txt"),
                      "initial_files": list(initial), "outputs_initially_empty": True,
                      "submitted": False}, ensure_ascii=False))


def export(product, case, attempt=1):
    name, workspace, private, destination = locations(product, case, attempt)
    if destination.exists():
        raise FileExistsError("Refuse overwrite or selective re-export of a public pilot")
    plan = read(private / "plan.json")
    start = read(private / "execution-start.json")
    finish = read(private / "execution-end.json")
    execution_status = finish.get("status") if finish.get("status") in ("completed", "failed") else None
    legacy_product_failure = product == "doubao" and execution_status == "failed" and bool(finish.get("infra_failure"))
    product_side_failure = True if legacy_product_failure or finish.get("product_side_failure") is True else False if execution_status == "completed" else None
    product_failure_label = finish.get("product_failure_label") or (finish.get("infra_failure") if legacy_product_failure else None)
    safe_public_text(json.dumps(product_failure_label, ensure_ascii=False))
    review = read(private / "public-review.json")
    receipts = read(private / "download-receipts.json")
    if review.get("review_actor") != "Operator/agent" or not review.get("redaction_reviewed") or not review.get("artifacts_privacy_reviewed"):
        raise ValueError("Explicit operator/agent review of public AX slices and native artifacts is required")
    if review.get("output_repairs_by_evaluator") is not False:
        raise ValueError("Review must explicitly record that no participant output was repaired")
    if (plan["run_id"] != name or plan.get("attempt", 1) != attempt or plan["workspace"] != str(workspace)
            or plan["product_id"] != product or plan["case_id"] != case):
        raise ValueError("Preparation identity/workspace changed")
    initial = read(private / "initial-inventory.json")
    current = inventory(workspace)
    if not all(current.get(path) == digest for path, digest in initial.items()):
        raise ValueError("Canonical initial prompt/input changed; retain privately for separate review")
    if sha(ROOT / "config/protocol.json") != plan["source_protocol_sha256"] or sha(ROOT / "cases" / case / "case.json") != plan["source_case_spec_sha256"]:
        raise ValueError("Protocol/case changed after preparation")
    if sha(private / "submitted-prompt.txt") != plan["submitted_prompt_sha256"]:
        raise ValueError("Recorded paste source changed after preparation")
    final_input_paths = set(inventory(workspace / "inputs"))
    initial_input_paths = {path.removeprefix("inputs/") for path in initial if path.startswith("inputs/")}
    allowed_late_inputs = {"rates.json"} if case == "T04" and (private / "release.json").exists() else set()
    if final_input_paths - initial_input_paths - allowed_late_inputs:
        raise ValueError("Unexpected additional input; preserve privately for explicit review")
    started = timestamp(start["started_at"])
    completed = timestamp(finish["completion_observed_at"])
    elapsed = (completed - started).total_seconds()
    if elapsed < 0 or (elapsed > 1200 and not finish.get("timed_out")):
        raise ValueError("Invalid pilot observation interval or missing timeout declaration")
    captures = [json.loads(line) for line in (private / "capture-log.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_label = {row["label"]: row for row in captures}
    if len(by_label) != len(captures):
        raise ValueError("Capture labels must be unique")
    events = []
    selected_lines = {}
    for selection in review["selections"]:
        capture = by_label[selection["capture"]]
        timestamp(capture["at"])
        ax = safe_path(private, capture["ax"])
        lines = ax.read_text(encoding="utf-8").splitlines()
        numbers = expand_ranges(selection["line_ranges"], len(lines))
        labels = []
        for number in numbers:
            text = lines[number - 1].strip()
            safe_public_text(text)
            labels.append({"source_line": number, "text": text})
        if not labels or capture["label"] in selected_lines:
            raise ValueError("Each reviewed capture must have one nonempty exact selection")
        selected_lines[capture["label"]] = set(numbers)
        events.append({"event_id": "ui-" + str(capture["index"]), "kind": "native_ui_observation",
                       "received_at": capture["at"], "phase": capture["label"], "labels": labels,
                       "private_ax_sha256": sha(ax),
                       "collection_scope": "Operator/agent-reviewed exact visible AX slices; not a native tool-call or model stream"})
    if not events:
        raise ValueError("Cannot export preparation as actual product evidence")
    events.sort(key=lambda event: timestamp(event["received_at"]))

    def evidence_reference(label, ranges):
        if label not in selected_lines:
            raise ValueError("Receipt evidence must appear in the reviewed public events")
        capture = by_label[label]
        count = len(safe_path(private, capture["ax"]).read_text(encoding="utf-8").splitlines())
        numbers = expand_ranges(ranges, count)
        if not numbers or not set(numbers).issubset(selected_lines[label]):
            raise ValueError("Receipt line references were not reviewed for publication")
        return {"event_id": "ui-" + str(capture["index"]), "capture": label,
                "line_ranges": ranges, "private_ax_sha256": sha(safe_path(private, capture["ax"]))}

    native_folder = private / "native-downloads"
    native_inventory = inventory(native_folder)
    artifacts = []
    registered_native = set()
    registered_outputs = {}
    receipt_ids = set()
    for artifact in receipts["artifacts"]:
        receipt_id = artifact["receipt_id"]
        safe_public_text(receipt_id)
        if receipt_id in receipt_ids:
            raise ValueError("Download receipt IDs must be unique")
        receipt_ids.add(receipt_id)
        native = safe_path(private, artifact["native_file"])
        if not native.is_relative_to(native_folder.resolve()):
            raise ValueError("Native original must stay in the dedicated download directory")
        relative_native = native.relative_to(native_folder.resolve()).as_posix()
        if relative_native in registered_native:
            raise ValueError("One receipt per native download; put ZIP member mappings in outputs[]")
        registered_native.add(relative_native)
        digest = sha(native)
        if digest != artifact["sha256"]:
            raise ValueError("Native download hash differs from the recorded receipt")
        origin = artifact["origin"]
        if origin not in ("native_download", "native_export", "native_local_file"):
            raise ValueError("Only actual native download/export/local-file originals are accepted")
        observed_at = (artifact.get("first_existence_observed_at") if origin == "native_local_file"
                       else artifact.get("downloaded_at") or artifact["download_available_observed_at"])
        timestamp(observed_at)
        save_action_at = artifact.get("save_action_at")
        if save_action_at and timestamp(save_action_at) > timestamp(observed_at):
            raise ValueError("Local presence observation precedes the recorded save action")
        local_source = artifact.get("native_workspace_relpath") if origin == "native_local_file" else None
        if origin == "native_local_file":
            if not local_source or not local_source.startswith("outputs/"):
                raise ValueError("Local originals require their actual relative participant output path")
            if safe_path(workspace, local_source).read_bytes() != native.read_bytes():
                raise ValueError("Local storage copy differs from the actual participant file")
        original_name = artifact["original_filename"]
        safe_public_text(original_name)
        reference = evidence_reference(artifact["evidence_capture"], artifact["evidence_line_ranges"])
        mappings = []
        for output in artifact["outputs"]:
            logical = output["logical_path"]
            destination_file = safe_path(workspace / "outputs", logical)
            if logical in registered_outputs:
                raise ValueError("Each logical output must have exactly one byte-source mapping")
            member = output.get("zip_member")
            if member is None:
                data = native.read_bytes()
            else:
                safe_public_text(member)
                with ZipFile(native) as archive:
                    if len([entry for entry in archive.infolist() if entry.filename == member]) != 1:
                        raise ValueError("ZIP member must exist exactly once")
                    data = archive.read(member)
            if destination_file.read_bytes() != data:
                raise ValueError("Logical output bytes differ from the native download/member")
            registered_outputs[logical] = hashlib.sha256(data).hexdigest()
            mappings.append({"logical_path": logical, "zip_member": member,
                             "bytes": len(data), "sha256": registered_outputs[logical]})
        artifacts.append({"receipt_id": receipt_id, "origin": artifact["origin"],
                          "original_filename": original_name, "public_native_file": "native-downloads/" + relative_native,
                          "downloaded_at": artifact.get("downloaded_at") if origin != "native_local_file" else None,
                          "download_available_observed_at": artifact.get("download_available_observed_at") if origin != "native_local_file" else None,
                          "download_time_visibility": ("No exact native completion receipt; later local-presence observation is an upper bound"
                                                       if origin != "native_local_file" and artifact.get("downloaded_at") is None
                                                       else "Recorded local-file observation or native completion time; not a server attestation"),
                          "save_action_at": save_action_at,
                          "save_action_source_line": artifact.get("save_action_source_line"),
                          "private_operator_actions_sha256": artifact.get("private_operator_actions_sha256"),
                          "first_existence_observed_at": observed_at if origin == "native_local_file" else None,
                          "native_workspace_relpath": local_source,
                          "source_projection": "Byte-preserving storage copy of native participant local file; no download claimed" if origin == "native_local_file" else "Original native download/export saved without content changes",
                          "bytes": native.stat().st_size,
                          "sha256": digest, "evidence": reference, "outputs": mappings,
                          "remote_url_visibility": "not_published; signed/internal links remain private"})
    if registered_native != set(native_inventory):
        raise ValueError("All native downloads, including extras/failures, must have receipts and be preserved")
    if registered_outputs != inventory(workspace / "outputs"):
        raise ValueError("All logical outputs, including extras, must match native download sources")

    released = None
    if (private / "release.json").exists():
        if case != "T04":
            raise ValueError("A planned input release is allowed only for T04")
        raw_release = read(private / "release.json")
        released = verify_remote_release(raw_release, plan, private, by_label, started, evidence_reference)
    visible_conditions = {}
    for key in ("mode_visible", "mode_observation_scope", "execution_location_visible", "version_visible", "installed_binary_version", "version_evidence_scope", "model_visible", "model_selector_changed", "account_tier",
                "permission_visible", "memory_condition", "skill_condition", "network_control_visible", "region"):
        value = review.get("visible_conditions", {}).get(key, "unknown")
        safe_public_text(json.dumps(value, ensure_ascii=False))
        visible_conditions[key] = value
    upload_mapping = []
    expected_inputs = {row["logical_path"] for row in plan["attachment_path_mapping"]}
    for upload in review.get("attachment_mapping", []):
        if upload["logical_path"] not in expected_inputs:
            raise ValueError("Initial attachment mapping contains an unexpected input")
        item = {key: upload.get(key) for key in ("logical_path", "actual_attachment_name", "upload_status", "accepted_observed_at")}
        safe_public_text(json.dumps(item, ensure_ascii=False))
        item["actual_server_path"] = None
        item["evidence"] = evidence_reference(upload["evidence_capture"], upload["evidence_line_ranges"])
        upload_mapping.append(item)
    issues = review.get("collector_issues", [])
    retrieval_limits = review.get("retrieval_limitations", [])
    unscheduled = review.get("unscheduled_prompts")
    safe_public_text(json.dumps({"issues": issues, "retrieval_limits": retrieval_limits, "unscheduled_prompts": unscheduled, "completion_basis": finish["completion_basis"]}, ensure_ascii=False))
    collector_source = private / "collector-source"
    if collector_source.exists() and not review.get("collector_sources_privacy_reviewed"):
        raise ValueError("Actual collector source snapshots require privacy review before publication")
    if collector_source.exists():
        for path in collector_source.rglob("*"):
            if path.is_file():
                safe_path(collector_source, path.relative_to(collector_source).as_posix())

    # All required review/provenance checks happen before creating the public directory.
    destination.mkdir(parents=True)
    shutil.copyfile(workspace / "prompt.md", destination / "case-prompt.md")
    shutil.copyfile(private / "submitted-prompt.txt", destination / "submitted-prompt.txt")
    shutil.copytree(workspace / "inputs", destination / "inputs")
    shutil.copytree(workspace / "outputs", destination / "outputs")
    shutil.copytree(native_folder, destination / "native-downloads")
    if inventory(destination / "outputs") != registered_outputs or inventory(destination / "native-downloads") != native_inventory:
        raise ValueError("Artifact bytes changed while exporting; incomplete package retained for audit")
    shutil.copytree(private / "prepare-source", destination / "prepare-source")
    if collector_source.exists():
        shutil.copytree(collector_source, destination / "collector-source")
    if (private / "record-adaptation.json").exists():
        adaptation = read(private / "record-adaptation.json")
        safe_public_text(json.dumps(adaptation, ensure_ascii=False))
        save(destination / "record-adaptation.json", adaptation)
    if (private / "native-binary-version.json").exists():
        binary_version = read(private / "native-binary-version.json")
        safe_public_text(json.dumps(binary_version, ensure_ascii=False))
        save(destination / "native-binary-version.json", binary_version)
    if (private / "operator-actions-public.jsonl").exists():
        operator_actions = (private / "operator-actions-public.jsonl").read_bytes()
        safe_public_text(operator_actions.decode("utf-8"))
        shutil.copyfile(private / "operator-actions-public.jsonl", destination / "operator-actions.jsonl")
    export_source = destination / "export-source"
    export_source.mkdir()
    shutil.copyfile(__file__, export_source / Path(__file__).name)
    if released:
        if not (destination / "inputs/rates.json").exists():
            shutil.copyfile(private / "held-release/rates.json", destination / "inputs/rates.json")
        shutil.copyfile(private / "supplement-prompt.txt", destination / "supplement-prompt.txt")
        save(destination / "release.json", released)
    (destination / "visible-events.jsonl").write_bytes(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events).encode("utf-8"))
    save(destination / "download-receipts.json", {"schema": "native-artifact-source-receipts-public-v1", "artifacts": artifacts,
        "private_original_receipts_sha256": sha(private / "download-receipts.json"),
        "basis": "Recorded native UI action/card evidence and retained native download/export/local-file originals; origin is explicit per artifact"})
    verification = evaluate(ROOT / "cases" / case, destination / "outputs")
    save(destination / "verification.json", verification)
    metadata = {
        "schema": "office-harness-pilot-v1", "run_id": name, "product_id": product, "case_id": case, "attempt": attempt,
        "track": "pilot", "formal_eligible": False, "formal_sample": False,
        "execution_status": execution_status,
        "execution_status_basis": "Recorded execution-end.status; never inferred from objective checks" if execution_status else "Recorded status absent or outside completed/failed; not inferred from objective checks",
        "product_side_failure": product_side_failure, "product_failure_label": product_failure_label,
        "failure_label_semantics": "Legacy infra_failure describes the Doubao product-reported failure, not evaluator infrastructure invalidity" if legacy_product_failure else "Explicit product-side failure declaration in execution-end" if finish.get("product_side_failure") is True else None,
        "surface": "native_desktop_office_task_via_documented_native_CUA",
        "visible_conditions": visible_conditions, "underlying_model_version": None,
        "model_visibility": "Visible UI label if captured; dynamic/backend routing unknown, not attested",
        "active_skills": None, "skills_disabled_verified": False, "actual_tool_calls": None,
        "os_sandbox_verified": False, "network_absence_independently_verified": False,
        "remote_filesystem_visibility": "unknown; local staging paths do not attest server paths or permissions",
        "attachment_mapping": upload_mapping, "attachment_mapping_complete": {row['logical_path'] for row in upload_mapping} == expected_inputs,
        "started_at": start["started_at"], "start_basis": start.get("start_basis", "Operator timestamp around native submit; precise service receipt unknown"),
        "completion_observed_at": finish["completion_observed_at"], "completion_basis": finish["completion_basis"],
        "elapsed_to_completion_observation_seconds": elapsed, "timed_out": finish.get("timed_out", False),
        "timeout_seconds": 1200, "timing_basis": "Submit-action/observation to observed completion; service timing unknown; download times reported separately",
        "initial_inventory": initial, "original_inputs_and_prompt_unchanged": True,
        "final_local_inventory": current, "case_prompt_sha256": sha(destination / "case-prompt.md"),
        "recorded_paste_source_sha256": sha(destination / "submitted-prompt.txt"),
        "actual_paste_source_sha256": sha(destination / "submitted-prompt.txt") if review.get("paste_source_used") is True else None,
        "actual_paste_source_visibility": "Operator/agent-attested source used in native paste" if review.get("paste_source_used") is True else "Prepared paste file only; use not attested in review",
        "actual_wire_bytes_sha256": None,
        "prompt_adapter_appendix": APPENDIX, "prompt_transport": "Recorded UTF-8 paste source; native UI submit observed; outbound/internal model-request bytes unknown",
        "prepare_source_sha256": inventory(destination / "prepare-source"), "export_source_sha256": inventory(export_source),
        "collector_source_sha256": inventory(destination / "collector-source") if collector_source.exists() else None,
        "checker_snapshot": {path: sha(ROOT / path) for path in ("harness_eval/core.py", "config/protocol.json", "config/rubric.json", f"cases/{case}/case.json", f"cases/{case}/oracle.json")},
        "private_capture_sha256": {row["ax"]: sha(safe_path(private, row["ax"])) for row in captures},
        "product_deliverables": inventory(destination / "outputs"), "native_originals": inventory(destination / "native-downloads"),
        "native_original_storage_directory": "native-downloads is a storage directory name; actual download/export/local-file origin is recorded per receipt",
        "download_receipts_sha256": sha(destination / "download-receipts.json"), "release": released,
        "output_repairs_by_evaluator": False, "unscheduled_prompts": unscheduled,
        "objective_score": verification["objective_score"], "manual_score": None, "total_score": None, "pure_harness_score": None,
        "evidence_level": "E2; selected visible native UI observations plus native downloaded/exported/local artifact bytes" if native_inventory else "E2; selected visible native UI observations only; no product artifact bytes obtained",
        "public_review_actor": "Operator/agent; no external human audit claimed", "collector_issues": issues,
        "retrieval_limitations": retrieval_limits,
        "redaction": "Exact operator/agent-reviewed AX slices only; raw screenshots, thinking/planning, hidden system/Skill text, account/history, private paths and signed URLs excluded",
        "visible_events_order": "Stable chronological received_at; source_line refers to private AX source, not a tool-call sequence",
        "visible_events_projection_sha256": sha(destination / "visible-events.jsonl"),
        "confidence": "High for preserved native-original/output byte equality and deterministic checks; E2 provenance depends on cited actual UI observations; internal causation unresolved" if native_inventory else "High for the recorded empty local native-original/output inventories and deterministic checks; failure evidence depends on cited actual UI observations; internal causation unresolved",
        "attribution": "One recorded end-to-end configuration; no isolated Model/Skill/Harness causal score",
        "limitations": ["Preparation and file hashes do not prove remote input decoding, file paths or server execution.",
                        "Visible labels and replies do not attest backend model, active Skills or full actual tool/network actions.",
                        "All native originals are retained; local storage copies do not imply download, and archive-member mappings are transparent storage operations, not output repair.",
                        "One exploratory pilot, not a formal replicate; no external human audit claimed."],
    }
    save(destination / "metadata.json", metadata)
    passed = sum(check["passed"] for check in verification["checks"])
    artifact_summary = ("原生原件全部保留，逻辑 outputs 逐字节对应 download-receipts 的原件/归档成员。origin 区分真实下载/导出与原生本地文件的存储复制，native-downloads 目录名不表示所有文件是下载。"
                        if native_inventory else "本次没有取得产品产物原件；native-downloads 与 outputs 清单均为空，没有创建或补写产物。")
    readme = (f"# {product} {case} 原生办公入口预试\n\n"
              f"真实条件与可见模式见 metadata；不从准备计划推定模式、版本或底层模型。{artifact_summary}客观检查 {passed}/{len(verification['checks'])}，{verification['objective_score']}/60；没有修复产物。\n\n"
              f"提交至完成观察区间 {elapsed:.3f} 秒；服务精确时刻不可见，下载时间另列。现场为 E2 的用户可见 AX 摘录{'和取得的原生产物字节' if native_inventory else '；本次未取得产品产物字节'}，未提取完整工具流或隐藏思考。模式、模型动态路由、Skill、远端权限和网络隔离不作未知事实的补全。\n\n"
              "prepare-source 是准备时的历史源码快照，export-source 是实际导出时的源码快照；二者可能因导出器继续实现而不同，历史原字节保留。submitted-prompt 是准备的粘贴源记录，是否实际采用见 actual_paste_source_visibility；actual wire bytes 仍 unknown。\n\n"
              "预试 formal_eligible=false；人工分、总分和纯 Harness 分 null。公开内容由操作人/代理审阅，未声称外部人工审计。manifest 证明归档一致性，不能独立证明产品来源。\n")
    if released:
        readme += "\nT04 的 inputs/rates.json 是补发后的末态原件；初始只有 prompt 与 inputs/trades.csv。复现须暂扣 rates，再按 release 的请求/附件可用/消息提交观察时点提供。原可见任务连续不等于已知内部 session ID，incident 自述不替代补发现场。\n"
    if retrieval_limits:
        readme += "\n取得原件的限制：\n\n" + "\n".join("- " + item for item in retrieval_limits) + "\n"
    (destination / "README.md").write_bytes(readme.encode("utf-8"))
    save(destination / "manifest.json", inventory(destination, exclude=("manifest.json",)))
    print(json.dumps({"exported": name, "attempt": attempt, "execution_status": execution_status,
                      "product_side_failure": product_side_failure, "checks": f"{passed}/{len(verification['checks'])}",
                      "objective_score": verification["objective_score"], "native_originals": len(artifacts),
                      "formal_eligible": False}, ensure_ascii=False))


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Evidence times must include a timezone")
    return parsed


def safe_path(base, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Evidence path must be a relative path within its dedicated directory")
    resolved = (base / path).resolve()
    if not resolved.is_relative_to(base.resolve()) or (base / path).is_symlink():
        raise ValueError("Evidence path escapes its directory")
    return resolved


def safe_public_text(text):
    # Supplemental guard only; semantic operator/agent review is still mandatory.
    if re.search(r"[A-Z]:[/\\]+Users[/\\]|file://|(?:bearer\s+|sk-)[A-Za-z0-9_-]{12,}|[?&](?:token|access_token|signature|auth|key)=|\b(?:uid|user_id)\b", text, re.I):
        raise ValueError("Potential private path, credential or signed URL in public projection")
    if any(word in text.lower() for word in ("accountsnapshot", "nickname", "reasoning_content", "thinking", "system_prompt", "cookie:")) or "思考" in text:
        raise ValueError("Potential hidden thinking/system/account content in public projection")


def expand_ranges(ranges, maximum):
    numbers = []
    for first, last in ranges:
        if not isinstance(first, int) or not isinstance(last, int) or first < 1 or last < first or last > maximum:
            raise ValueError("AX line range outside actual source")
        numbers.extend(range(first, last + 1))
    if len(numbers) != len(set(numbers)):
        raise ValueError("AX line selection overlaps")
    return numbers


def verify_remote_release(record, plan, private, captures, started, reference):
    if record.get("semantics_reviewed") is not True or record.get("same_visible_task") is not True:
        raise ValueError("T04 requires reviewed real upload/message semantics in the same visible task")
    mode = record["mode"]
    if mode not in ("active", "passive"):
        raise ValueError("Explicit T04 active/passive mode required")
    uploaded = timestamp(record["upload_available_observed_at"])
    sent = timestamp(record["supplement_sent_observed_at"])
    if uploaded < started or sent < uploaded:
        raise ValueError("T04 remote availability and SENT message times must be ordered")
    if sent > started + timedelta(seconds=1200):
        raise ValueError("T04 supplemental input was not supplied within the pilot budget")
    request = None
    if mode == "active":
        observed = timestamp(record["request_observed_at"])
        if not 0 <= (observed - started).total_seconds() <= 120 or uploaded < observed:
            raise ValueError("T04 active request is outside the fixed 120-second window")
        request = reference(record["request_capture"], record["request_line_ranges"])
        if captures[record["request_capture"]]["at"] != record["request_observed_at"]:
            raise ValueError("T04 request observation time must match its real capture")
    elif (uploaded - started).total_seconds() < 120:
        raise ValueError("T04 passive release must not occur before 120 seconds")
    upload_evidence = reference(record["upload_capture"], record["upload_line_ranges"])
    message_evidence = reference(record["supplement_capture"], record["supplement_line_ranges"])
    held = private / plan["held_release"]["private_file"]
    if sha(held) != plan["held_release"]["sha256"]:
        raise ValueError("T04 held rate source changed")
    expected_message = plan["held_release"]["release_protocol"]["response_text"]
    if (private / "supplement-prompt.txt").read_bytes() != expected_message.encode("utf-8"):
        raise ValueError("T04 fixed response text changed")
    optional_local_rates = Path(plan["workspace"]) / "inputs/rates.json"
    if optional_local_rates.exists() and optional_local_rates.read_bytes() != held.read_bytes():
        raise ValueError("T04 local staging of the released rates differs from the held source")
    return {"mode": mode, "semantics_reviewed": True, "request_observed_at": record.get("request_observed_at"),
            "request_evidence": request, "upload_available_observed_at": record["upload_available_observed_at"],
            "upload_evidence": upload_evidence, "supplement_sent_observed_at": record["supplement_sent_observed_at"],
            "supplement_evidence": message_evidence, "source_file_sha256": sha(held),
            "actual_remote_bytes_sha256": None, "actual_remote_bytes_visibility": "unknown; local upload source and accepted UI attachment observed",
            "response_text": expected_message, "response_text_sha256": sha(private / "supplement-prompt.txt"),
            "same_visible_task": True, "native_session_id": None,
            "observer_delay_seconds": (uploaded - timestamp(record["request_observed_at"])).total_seconds() if mode == "active" else None,
            "message_after_file_observation_seconds": (sent - uploaded).total_seconds(),
            "local_file_copy_is_remote_availability_proof": False,
            "private_original_release_record_sha256": sha(private / "release.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "export"))
    parser.add_argument("--product", required=True, choices=("yuanbao", "doubao"))
    parser.add_argument("--case", required=True, choices=CASE_IDS)
    parser.add_argument("--attempt", type=int, default=1, help="Preserved pilot attempt number (>=1); default keeps existing r1 paths")
    args = parser.parse_args()
    if args.attempt < 1:
        parser.error("--attempt must be >=1")
    if args.action == "prepare":
        prepare(args.product, args.case, args.attempt)
    else:
        export(args.product, args.case, args.attempt)
