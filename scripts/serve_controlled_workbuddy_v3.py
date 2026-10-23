"""Operator-driven WorkBuddy v3 diagnostic host; never launches a product."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

try:
    from scripts.controlled_workbuddy_v3_fixture import BridgeServer, schema_digest
    from scripts.serve_controlled_workbuddy import (now, read, save_new, instant, digest, encoded,
                                                   safe_relative, wait_for_operator, collect_artifact)
except ModuleNotFoundError:
    from controlled_workbuddy_v3_fixture import BridgeServer, schema_digest
    from serve_controlled_workbuddy import (now, read, save_new, instant, digest, encoded,
                                          safe_relative, wait_for_operator, collect_artifact)


ROOT = Path(__file__).resolve().parents[1]
BASE = "supplements/controlled-workbuddy-v3"
WORK = Path("D:/harness-controlled-workbuddy-v3")


def verify_registration(root, run_id, phase, commit):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id) or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise ValueError("Invalid run or registration identity")
    relative = BASE + ("/calibration.json" if phase == "calibration" else "/protocol.json")
    raw = (root / relative).read_bytes()

    def blob(name):
        return subprocess.check_output(["git", "show", commit + ":" + name], cwd=root, stderr=subprocess.PIPE)

    if blob(relative) != raw:
        raise ValueError("Protocol differs from registered blob")
    protocol = read(root / relative)
    if protocol.get("phase") != phase or protocol.get("timeout_seconds") != 120 or protocol.get("max_auxiliary_requests") != 3:
        raise ValueError("Protocol phase or fixed budgets differ")
    for name, spec in protocol["files"].items():
        data = safe_relative(root, name).read_bytes()
        if len(data) != spec["bytes"] or digest(data) != spec["sha256"] or blob(name) != data:
            raise ValueError("Frozen source differs: " + name)
    runs = [row for row in protocol["runs"] if row["run_id"] == run_id]
    if len(runs) != 1 or runs[0]["product_id"] != "workbuddy" or runs[0]["mode"] not in {"success", "error"}:
        raise ValueError("Unregistered WorkBuddy diagnostic")
    fixture = read(root / BASE / "fixture.json")
    schema = read(root / BASE / "tool-schema.json")
    for required in (BASE + "/fixture.json", BASE + "/tool-schema.json", "scripts/controlled_probe_mcp.py"):
        if required not in protocol["files"]:
            raise ValueError("Required frozen source is unbound")
    return protocol, runs[0], fixture, schema


def serve_run(run_id, phase, registration, *, repo_root=ROOT, work_root=WORK, private_root=None):
    repo_root, work_root = Path(repo_root), Path(work_root)
    private_root = Path(private_root) if private_root else repo_root / "private/controlled-workbuddy-v3"
    protocol, spec, fixture, schema = verify_registration(repo_root, run_id, phase, registration)
    runroot, evidence = work_root / run_id, private_root / run_id
    if runroot.exists() or evidence.exists():
        raise FileExistsError("Refusing diagnostic run/evidence overwrite")
    runroot.parent.mkdir(parents=True, exist_ok=True); evidence.parent.mkdir(parents=True, exist_ok=True)
    runroot.mkdir(exist_ok=False); evidence.mkdir(exist_ok=False)
    workspace, runtime = runroot / "work", runroot / "runtime"
    workspace.mkdir(); runtime.mkdir()
    tool = runtime / "controlled_probe_mcp.py"
    shutil.copyfile(repo_root / "scripts/controlled_probe_mcp.py", tool)
    host_at, began = now(), time.monotonic()
    result = {"run_id": run_id, "phase": phase, "product_id": "workbuddy", "mode": spec["mode"],
              "adapter_version": "controlled-workbuddy/v3", "registration_commit": registration,
              "registration_file": "calibration.json" if phase == "calibration" else "protocol.json",
              "host_started_at": host_at, "started_at": None, "actual_submitted": False,
              "model_kind": "deterministic_local_transport_fixture", "real_model_inference": False,
              "version": "V5.8.3", "version_basis": "operator UI observation, not queried by host",
              "shared_tool_sha256": digest(tool.read_bytes()),
              "frozen_arguments_sha256": digest(encoded(fixture["arguments"])),
              "schema_sha256": schema_digest(schema), "timeout_seconds": 120,
              "preparation_timeout_seconds": 900, "max_auxiliary_requests": 3,
              "runtime_errors": [], "artifact": None, "stop_basis": None, "deadline_expired": False,
              "native_completion": "unknown; operator observes it separately"}
    state = None
    try:
        with BridgeServer(fixture["arguments"], schema, spec["mode"], evidence / "model-events.jsonl") as server:
            state = server.state
            mcp_args = [str(tool), "--workspace", str(workspace), "--mode", spec["mode"], "--journal", str(evidence / "mcp-events.jsonl")]
            ready = {"run_id": run_id, "adapter_version": "controlled-workbuddy/v3", "base_url": server.base_url,
                     "chat_url": server.base_url + "/chat/completions", "python": sys.executable,
                     "mcp_command": sys.executable, "mcp_args": mcp_args, "mcp_server_name": "contract",
                     "workspace": str(workspace), "runroot": str(runroot), "evidence": str(evidence),
                     "version": "V5.8.3", "shared_tool_sha256": result["shared_tool_sha256"],
                     "submission_file": str(evidence / "submission.json"), "stop_file": str(evidence / "stop.json"),
                     "timeout_seconds": 120, "preparation_timeout_seconds": 900, "max_auxiliary_requests": 3,
                     "schema_sha256": result["schema_sha256"], "product_process_started_by_host": False}
            save_new(evidence / "ready.json", ready)
            print(json.dumps({"ready": str(evidence / "ready.json"), "chat_url": ready["chat_url"]}), flush=True)
            observation = wait_for_operator(evidence, host_at, lambda: state.requests)
            result.update({key: value for key, value in observation.items() if key != "submission"})
            if observation["submission"] is not None:
                result.update(actual_submitted=True, started_at=observation["submission"]["at"])
    except (Exception, KeyboardInterrupt) as error:
        result["stop_basis"] = "host_runtime_error"
        result["runtime_errors"].append({"type": type(error).__name__, "message": "Host exception; operator evidence retained"})
    finally:
        if not result["actual_submitted"] and (evidence / "submission.json").is_file():
            try:
                submission = read(evidence / "submission.json")
                if (submission.get("actual_submitted") is True and submission.get("method") == "native_computer_use"
                        and instant(host_at) <= instant(submission["at"]) <= instant(now())):
                    result.update(actual_submitted=True, started_at=submission["at"])
            except (OSError, ValueError, KeyError, AttributeError):
                pass
        try:
            result["artifact"] = collect_artifact(workspace, evidence)
        except Exception as error:
            result["runtime_errors"].append({"type": type(error).__name__, "message": "Artifact collection failed"})
        result.update(local_model_requests=state.requests if state else 0,
                      main_model_requests=state.main_model_requests if state else 0,
                      auxiliary_requests=state.auxiliary_requests if state else 0,
                      rejected_requests=state.rejected_requests if state else 0,
                      fixture_rejected=state.failed if state else None,
                      discovery_model_requests=state.discovery_model_requests if state else 0,
                      discovery_calls=state.discovery_calls if state else 0,
                      discovery_return_sha256=state.discovery_return_sha256 if state else None,
                      ended_at=now(), host_elapsed_seconds=time.monotonic() - began,
                      product_process_started_by_host=False, product_stop_performed_by_host=False)
        save_new(evidence / "execution.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", choices=("calibration", "main"), required=True)
    parser.add_argument("--registration", required=True)
    args = parser.parse_args()
    outcome = serve_run(args.run_id, args.phase, args.registration)
    raise SystemExit(1 if outcome["runtime_errors"] else 0)
