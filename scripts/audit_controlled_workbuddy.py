"""Export and audit reviewed WorkBuddy diagnostics without GUI or model access.

Only completed local fixture records and an explicitly reviewed gui-scene.json
are read. No AX file, screenshot, product database, user config or Skill is read.
Source hashes establish consistency, not independent observer authentication.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MARKER = "CONTROLLED_TOOL_V1"
CALL_ID = "call_controlled_1"
TARGETS = {"mcp__contract__probe_commit", "mcp__custom-mcp__contract__probe_commit",
           "mcp__custom_mcp__contract__probe_commit"}
PUBLIC_REJECTION_REASONS = {
    "ToolSearch declaration cannot validate the fixed bridge arguments",
    "Earlier request was rejected; no in-run adaptation",
}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha(data): return hashlib.sha256(data).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read(path): return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def lines(path):
    return [json.loads(line, object_pairs_hook=unique) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def save_lines(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8", newline="\n")


def pick(value, keys): return {key: value[key] for key in keys if key in value}


def markers(value):
    if isinstance(value, dict):
        if value.get("marker") == MARKER: return [value]
        return [result for child in value.values() for result in markers(child)]
    if isinstance(value, list): return [result for child in value for result in markers(child)]
    if isinstance(value, str):
        try: decoded = json.loads(value, object_pairs_hook=unique)
        except ValueError: return []
        return markers(decoded)
    return []


def expected_payload(fixture, mode):
    data = fixture["arguments"]["text"].encode("utf-8")
    return ({"marker": MARKER, "mode": "success", "bytes": len(data), "sha256": sha(data)}
            if mode == "success" else {"marker": MARKER, "mode": "error", "code": "E_FIXTURE_DENIED"})


def sanitized_payload(payload):
    result = {"marker": MARKER}
    if payload.get("mode") in ("success", "error"): result["mode"] = payload["mode"]
    if type(payload.get("bytes")) is int: result["bytes"] = payload["bytes"]
    if isinstance(payload.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", payload["sha256"]): result["sha256"] = payload["sha256"]
    if payload.get("code") == "E_FIXTURE_DENIED": result["code"] = payload["code"]
    return result


def namespace_for(folder):
    name = folder.parent.name
    if name not in {"controlled-workbuddy-v1", "controlled-workbuddy-v2", "controlled-workbuddy-v3"}:
        raise ValueError("Unexpected WorkBuddy namespace")
    return name


def export_private(source, destination, *, root=ROOT, gui_scene=None):
    """Strict public whitelist. Never inspect GUI originals or arbitrary outputs."""
    source, destination, root = Path(source), Path(destination), Path(root)
    if not (source / "execution.json").is_file() or not (source / "stop.json").is_file():
        raise ValueError("Run has not ended with execution and operator stop records")
    namespace = namespace_for(source)
    execution = read(source / "execution.json")
    fixture = read(root / "supplements" / namespace / "fixture.json")
    expected = expected_payload(fixture, execution["mode"])
    if destination.exists(): raise FileExistsError("Refusing public package overwrite")
    destination.mkdir(parents=True, exist_ok=False)
    allowed_exec = ("run_id", "phase", "product_id", "mode", "adapter_version", "registration_commit", "registration_file",
                    "host_started_at", "started_at", "ended_at", "actual_submitted", "timeout_seconds", "preparation_timeout_seconds",
                    "model_kind", "real_model_inference", "version", "version_basis", "shared_tool_sha256", "frozen_arguments_sha256",
                    "schema_sha256", "artifact", "stop_basis", "deadline_expired", "local_model_requests", "main_model_requests",
                    "auxiliary_requests", "rejected_requests", "fixture_rejected", "discovery_calls", "discovery_model_requests",
                    "discovery_return_sha256", "host_elapsed_seconds", "elapsed_seconds", "product_process_started_by_host",
                    "product_stop_performed_by_host")
    public_exec = pick(execution, allowed_exec)
    public_exec["adapter_version"] = execution.get("adapter_version", "controlled-workbuddy/v1")
    public_exec["runtime_error_types"] = [row.get("type") for row in execution.get("runtime_errors", [])]
    if isinstance(public_exec.get("artifact"), dict):
        public_exec["artifact"] = pick(public_exec["artifact"], ("bytes", "sha256", "acquired_at", "source_stable_during_copy"))
    public_exec["source_execution_sha256"] = sha((source / "execution.json").read_bytes())
    save(destination / "execution.json", public_exec)
    ready = read(source / "ready.json")
    save(destination / "ready.json", pick(ready, ("run_id", "phase", "mode", "product_id", "adapter_version", "host_started_at",
         "base_url", "chat_url", "version", "shared_tool_sha256", "mcp_server_name", "mcp_tool_name", "schema_sha256",
         "timeout_seconds", "preparation_timeout_seconds", "max_auxiliary_requests", "product_process_started_by_host")))
    model = []
    allowed_model = ("at", "kind", "sequence", "path", "request_sha256", "request_bytes", "model", "model_is_expected",
                     "tool_candidates", "tool_metadata", "tool_return_count", "matched_fixed_call_count", "fixed_call_id_present",
                     "fixture_return_payloads", "exact_fixture_payload_match", "main_stage_before", "arguments_sha256",
                     "native_tool", "canonical_tool", "main_sequence", "call_id", "registered_schema_sha256",
                     "auxiliary_sequence", "classification", "error_type", "metadata_parse_failed", "discovery_calls_before",
                     "matched_search_count", "matched_probe_count", "discovery_sequence", "schema_sha256", "validation_schema",
                     "content_bytes", "content_sha256", "tool_reference_names", "discovery_bridge_used", "name")
    if (source / "model-events.jsonl").is_file():
        for number, row in enumerate(lines(source / "model-events.jsonl"), 1):
            selected = pick(row, allowed_model)
            metadata_fields = ("name", "namespace", "canonical_name", "schema_sha256", "schema_present", "invalid_name_sha256")
            for field in ("tool_candidates", "tool_metadata"):
                if field in selected: selected[field] = [pick(item, metadata_fields) for item in selected[field]]
            if isinstance(selected.get("native_tool"), dict): selected["native_tool"] = pick(selected["native_tool"], metadata_fields)
            selected.update(source_line=number, source_event_sha256=sha(encoded(row)))
            if row.get("arguments") == fixture["arguments"]: selected["arguments"] = row["arguments"]
            elif row.get("arguments") == {"query": "+contract probe_commit", "max_results": 1}: selected["arguments"] = row["arguments"]
            elif "arguments" in row: selected["source_arguments_match"] = False
            if row.get("text") in {"CONTROLLED_DONE", "CONTROLLED_AUXILIARY"}: selected["text"] = row["text"]
            # A rejection can contain arbitrary upstream data in a future
            # producer. Only these already reviewed fixed producer literals
            # may be public; never copy an exception message indiscriminately.
            if (row.get("kind") == "fixture_rejection" and isinstance(row.get("reason"), str)
                    and row["reason"] in PUBLIC_REJECTION_REASONS):
                selected["reason"] = row["reason"]
            selected["fixture_return_payloads"] = [sanitized_payload(p) for p in row.get("fixture_return_payloads", [])]
            model.append(selected)
    save_lines(destination / "model-events.jsonl", model)
    mcp = []
    if (source / "mcp-events.jsonl").is_file():
        for number, row in enumerate(lines(source / "mcp-events.jsonl"), 1):
            request, response = row.get("request", {}), row.get("response") or {}
            params = request.get("params", {})
            result = response.get("result", {})
            selected = {"kind": "mcp_event", "method": request.get("method"), "source_line": number,
                        "source_event_sha256": sha(encoded(row)), "request_id": request.get("id"),
                        "response_id": response.get("id"), **pick(row, ("received_at", "completed_at", "elapsed_ms", "mode"))}
            if request.get("method") == "tools/call":
                payloads = markers(result.get("content"))
                selected.update(kind="mcp_call", tool_name=params.get("name"),
                    arguments=params.get("arguments") if params.get("arguments") == fixture["arguments"] else None,
                    arguments_match=params.get("arguments") == fixture["arguments"],
                    payloads=[sanitized_payload(p) for p in payloads], source_payload_exact=payloads == [expected],
                    is_error=result.get("isError"), source_result_sha256=sha(encoded(result)))
            mcp.append(selected)
    save_lines(destination / "mcp-events.jsonl", mcp)
    scene = Path(gui_scene) if gui_scene is not None else source / "gui-scene.json"
    if scene.is_file():
        approved = read(scene)
        public_scene = pick(approved, ("schema", "run_id", "task_accepted", "acceptance_basis", "observed_at", "interface",
                           "native_terminal", "fixed_terminal_text", "selected_model", "privacy", "confidence",
                           "native_cli_exit_code", "native_cli_exit_basis"))
        if "raw_source" in approved:
            public_scene["raw_source"] = pick(approved["raw_source"], ("private_original_sha256", "private_original_bytes",
                                                                      "capture_name", "lines", "disclosure"))
        save(destination / "gui-scene.json", public_scene)
    if (source / "collected/artifact.txt").is_file():
        (destination / "collected").mkdir()
        shutil.copyfile(source / "collected/artifact.txt", destination / "collected/artifact.txt")
    files = [{"path": path.relative_to(destination).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
             for path in sorted(destination.rglob("*")) if path.is_file()]
    save(destination / "manifest.json", {"schema": "reviewed-workbuddy-fixture-package/v1", "run_id": source.name,
                                         "namespace": namespace, "files": files})
    return destination


def manifest_check(folder):
    manifest = read(folder / "manifest.json")
    files = manifest["files"]
    names = [row["path"] for row in files]
    if len(names) != len(set(names)): raise ValueError("Duplicate inventory path")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != "manifest.json"}
    if actual != set(names): raise ValueError("Inventory differs")
    for row in files:
        name = PurePosixPath(row["path"])
        if name.is_absolute() or ".." in name.parts or "\\" in row["path"] or ":" in row["path"]: raise ValueError("Unsafe evidence path")
        path = folder / name
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()): raise ValueError("Evidence symlink/escape")
        if len(path.read_bytes()) != row["bytes"] or sha(path.read_bytes()) != row["sha256"]: raise ValueError("Inventory hash/size differs")
    return manifest


def audit_package(folder, *, root=ROOT, verify_git=True):
    folder, root = Path(folder), Path(root)
    result = {"run_id": folder.name, "outcome": "unknown", "task_accepted": False, "independent_tasks": 0,
              "product_failure": False, "phase": None, "checks": {}, "integrity_errors": [],
              "confidence": "public-record consistency only; one AI-assisted operator"}
    try:
        manifest = manifest_check(folder)
        execution = read(folder / "execution.json")
        namespace = manifest["namespace"]
        fixture_path = "supplements/" + namespace + "/fixture.json"
        fixture = read(root / fixture_path)
        expected = expected_payload(fixture, execution["mode"])
        model, mcp = lines(folder / "model-events.jsonl"), lines(folder / "mcp-events.jsonl")
        scene = read(folder / "gui-scene.json") if (folder / "gui-scene.json").is_file() else {}
        result.update(phase=execution["phase"], namespace=namespace, actual_submitted=execution.get("actual_submitted") is True,
                      adapter_version=execution.get("adapter_version"), mode=execution["mode"])
        checks = result["checks"]
        def check(name, passed): checks[name] = bool(passed)
        requests = [row for row in model if row.get("kind") == "model_request"]
        excerpts = scene.get("raw_source", {}).get("lines", [])
        accepted = (scene.get("run_id") == folder.name and scene.get("task_accepted") is True
                    and bool(scene.get("acceptance_basis")) and bool(requests)
                    and any("这是固定工具契约实验" in text for text in excerpts))
        result["task_accepted"], result["independent_tasks"] = accepted, int(accepted)
        check("native_task_accepted", accepted)
        check("identity", execution["run_id"] == folder.name and execution["product_id"] == "workbuddy")
        check("actual_submitted", result["actual_submitted"])
        check("request_count", execution.get("local_model_requests") == len(requests))
        check("request_sequences", [row.get("sequence") for row in requests] == list(range(1, len(requests) + 1)))
        fixed = [row for row in model if row.get("kind") == "fixed_tool_request"]
        calls = [row for row in mcp if row.get("kind") == "mcp_call"]
        auxiliary = [row for row in model if row.get("kind") == "fixed_auxiliary"]
        discovery = [row for row in model if row.get("kind") == "fixed_discovery_request"]
        result.update(total_model_requests=len(requests), auxiliary_requests=len(auxiliary),
                      discovery_calls=len(discovery), probe_dispatches=len(fixed), actual_mcp_calls=len(calls),
                      fixture_rejection_events=sum(row.get("kind") == "fixture_rejection" for row in model),
                      transport_error_events=sum(row.get("kind") == "fixture_transport_error" for row in model),
                      host_stop_basis=execution.get("stop_basis"), host_deadline_expired=execution.get("deadline_expired"),
                      native_completion_observed=scene.get("native_terminal", {}).get("normal") is True)
        if "auxiliary_requests" in execution:
            check("auxiliary_count", execution["auxiliary_requests"] == len(auxiliary))
        if "discovery_calls" in execution:
            check("discovery_count", execution["discovery_calls"] == len(discovery))
        if "rejected_requests" in execution:
            check("rejection_count", execution["rejected_requests"] == result["fixture_rejection_events"])
        check("auxiliary_bound", len(auxiliary) <= 3)
        check("discovery_bound", len(discovery) <= 1)
        if discovery:
            check("fixed_discovery_arguments", discovery[0].get("call_id") == "call_search_1"
                  and discovery[0].get("arguments") == {"query": "+contract probe_commit", "max_results": 1})
            discovery_returns = [row for row in model if row.get("kind") == "discovery_return"]
            check("actual_discovery_return", len(discovery_returns) == 1
                  and discovery_returns[0].get("call_id") == "call_search_1"
                  and isinstance(discovery_returns[0].get("content_bytes"), int)
                  and bool(re.fullmatch(r"[0-9a-f]{64}", discovery_returns[0].get("content_sha256", ""))))
        check("one_probe_dispatch", len(fixed) == 1)
        check("probe_arguments", len(fixed) == 1 and fixed[0].get("arguments") == fixture["arguments"]
              and fixed[0].get("arguments_sha256") == sha(encoded(fixture["arguments"])))
        schema = read(root / "supplements" / namespace / "tool-schema.json") if namespace != "controlled-workbuddy-v1" else None
        schema_sha = sha(json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()) if schema else None
        native_tool = fixed[0].get("native_tool", {}) if len(fixed) == 1 else {}
        check("exact_schema_and_name", bool(native_tool) and native_tool.get("canonical_name") in TARGETS
              and native_tool.get("schema_sha256") == schema_sha)
        check("one_actual_mcp_call", len(calls) == 1)
        check("actual_mcp_arguments_and_return", len(calls) == 1 and calls[0].get("tool_name") == "probe_commit"
              and calls[0].get("arguments") == fixture["arguments"] and calls[0].get("arguments_match") is True
              and calls[0].get("source_payload_exact") is True and calls[0].get("payloads") == [expected]
              and calls[0].get("request_id") == calls[0].get("response_id"))
        check("actual_mcp_error_flag", len(calls) == 1 and (calls[0].get("is_error") is True if execution["mode"] == "error"
                                                          else calls[0].get("is_error") in (False, None)))
        probe_returns = [row for row in requests if row.get("exact_fixture_payload_match") is True]
        check("actual_fixed_call_return", len(probe_returns) == 1 and probe_returns[0].get("fixture_return_payloads") == [expected]
              and (probe_returns[0].get("matched_probe_count") == 1 or probe_returns[0].get("matched_fixed_call_count") == 1))
        terminals = [row for row in model if row.get("kind") == "fixed_terminal" and row.get("text") == "CONTROLLED_DONE"]
        check("fixed_terminal", len(terminals) == 1)
        check("no_fixture_rejection", not any(row.get("kind") in {"fixture_rejection", "fixture_transport_error"} for row in model))
        check("native_completion", scene.get("native_terminal", {}).get("normal") is True
              and scene.get("fixed_terminal_text") == "CONTROLLED_DONE")
        result["native_terminal"] = scene.get("native_terminal")
        result["native_cli_exit_code"] = None
        result["native_cli_exit_basis"] = "Desktop UI terminal evidence is used; no CLI exit code exists"
        artifacts = list((folder / "collected").rglob("*")) if (folder / "collected").exists() else []
        artifacts = [p for p in artifacts if p.is_file()]
        data = fixture["arguments"]["text"].encode("utf-8")
        if execution["mode"] == "success":
            check("artifact_bytes", len(artifacts) == 1 and artifacts[0].name == "artifact.txt" and artifacts[0].read_bytes() == data)
        else: check("error_has_no_artifact", not artifacts and execution.get("artifact") is None)
        if verify_git:
            commit, filename = execution["registration_commit"], execution["registration_file"]
            if not re.fullmatch(r"[0-9a-f]{7,40}", commit) or filename not in {"calibration.json", "protocol.json"}: raise ValueError("Unsafe registration locator")
            def blob(name): return subprocess.check_output(["git", "show", commit + ":" + name], cwd=root, stderr=subprocess.PIPE)
            protocol_path = "supplements/" + namespace + "/" + filename
            historical = blob(protocol_path)
            if (root / protocol_path).read_bytes() != historical: raise ValueError("Historical protocol changed")
            protocol = json.loads(historical, object_pairs_hook=unique)
            run_spec = next(row for row in protocol["runs"] if row["run_id"] == folder.name)
            if run_spec["mode"] != execution["mode"] or run_spec["product_id"] != "workbuddy" or protocol["phase"] != execution["phase"]: raise ValueError("Run is not registered")
            for name, spec in protocol["files"].items():
                original = blob(name)
                if len(original) != spec["bytes"] or sha(original) != spec["sha256"]: raise ValueError("Frozen source blob hash differs")
            if blob(fixture_path) != (root / fixture_path).read_bytes(): raise ValueError("Fixture changed")
            if execution["shared_tool_sha256"] != protocol["files"]["scripts/controlled_probe_mcp.py"]["sha256"]: raise ValueError("Shared MCP hash differs")
            if execution["frozen_arguments_sha256"] != sha(encoded(fixture["arguments"])): raise ValueError("Argument hash differs")
            committed = subprocess.check_output(["git", "show", "-s", "--format=%cI", commit], cwd=root, text=True).strip()
            if datetime.fromisoformat(committed) > datetime.fromisoformat(execution["host_started_at"]): raise ValueError("Registration after host start")
            result["registration"] = {"commit": commit, "path": protocol_path, "sha256": sha(historical),
                                       "frozen_source_blobs": len(protocol["files"])}
        if all(checks.values()): result["outcome"] = "pass"
        result["failed_checks"] = [key for key, value in checks.items() if not value]
        result["product_failure"] = False  # This module currently publishes calibration records only.
        result["scope"] = "WorkBuddy calibration; auxiliary/discovery differ from C/D full chain; no product ranking"
    except (OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as error:
        result["integrity_errors"].append(type(error).__name__ + ": " + str(error))
        result["outcome"] = "unknown"
    return result


def build(root=ROOT):
    root = Path(root)
    packages = []
    for version in (1, 2, 3):
        base = root / f"public/supplements/controlled-workbuddy-v{version}"
        packages.extend(audit_package(folder, root=root) for folder in sorted(base.glob("WBC*")) if folder.is_dir())
    return {"schema": "controlled-workbuddy-public-audit/v1", "packages": packages,
            "counts": {"attempts": len(packages), "independent_tasks": sum(p["independent_tasks"] for p in packages),
                       "calibration_tasks": sum(p["independent_tasks"] for p in packages if p["phase"] == "calibration"),
                       "formal_tasks": sum(p["independent_tasks"] for p in packages if p["phase"] != "calibration"),
                       "passed": sum(p["outcome"] == "pass" for p in packages),
                       "unknown": sum(p["outcome"] == "unknown" for p in packages), "product_failures": 0},
            "limits": ["Only reviewed GUI scene is read; AX originals and screenshots remain private.",
                       "Submission is an attempt; native task acceptance needs its own scene.",
                       "Native UI error on calibration is not a product contract failure.",
                       "WorkBuddy discovery/auxiliary adapters differ from C/D v1; full-chain equal conditions are not claimed."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.export:
        if not args.destination: parser.error("--export requires --destination")
        export_private(args.export, args.destination, root=args.root)
    report = build(args.root)
    if args.output:
        if args.check:
            if read(args.output) != report: raise SystemExit("Published WorkBuddy audit is stale")
        else: save(args.output, report)
    print(json.dumps(report["counts"], ensure_ascii=False))
    raise SystemExit(1 if any(p["integrity_errors"] for p in report["packages"]) else 0)
