"""Serve frozen fixtures for an operator-controlled WorkBuddy desktop run.

This process starts only a loopback HTTP fixture. It never launches a product,
controls a desktop, reads existing user configuration, or calls remote inference.
Native task completion must be observed by the operator and recorded via stop.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import time

try:
    from scripts.controlled_model_fixture import FixtureServer
except ModuleNotFoundError:
    from controlled_model_fixture import FixtureServer


ROOT = Path(__file__).resolve().parents[1]
WORK = Path("D:/harness-controlled-workbuddy-v1")
BASE = "supplements/controlled-workbuddy-v1"
PREPARE_SECONDS = 900
TASK_SECONDS = 120
UI_VERSION = "V5.8.3"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def save_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def instant(value):
    value = datetime.fromisoformat(value)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Operator timestamp must have an explicit timezone")
    return value


def safe_relative(root, name):
    if not isinstance(name, str):
        raise ValueError("Registration file path must be a string")
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or ".." in relative.parts or ":" in name or "\\" in name:
        raise ValueError("Unsafe registration file path")
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Registration file escapes repository")
    return target


def verify_registration(root, run_id, phase, commit):
    root = Path(root)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("Unsafe run ID")
    if phase not in {"calibration", "main"} or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise ValueError("Invalid phase or registration commit")
    name = "calibration.json" if phase == "calibration" else "protocol.json"
    relative = BASE + "/" + name
    protocol_bytes = (root / relative).read_bytes()

    def blob(path):
        return subprocess.check_output(["git", "show", commit + ":" + path], cwd=root, stderr=subprocess.PIPE)

    if blob(relative) != protocol_bytes:
        raise ValueError("Current protocol differs from the registered git blob")
    protocol = json.loads(protocol_bytes, object_pairs_hook=unique_object)
    if protocol.get("phase") != phase or protocol.get("timeout_seconds", TASK_SECONDS) != TASK_SECONDS:
        raise ValueError("Protocol phase or 120-second task budget differs")
    files = protocol.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Registration must hash its supporting files")
    for name, spec in files.items():
        current = safe_relative(root, name).read_bytes()
        if len(current) != spec["bytes"] or digest(current) != spec["sha256"] or blob(name) != current:
            raise ValueError("Registered supporting file changed: " + name)
    matching = [row for row in protocol.get("runs", []) if row.get("run_id") == run_id]
    if len(matching) != 1 or matching[0].get("product_id") != "workbuddy" or matching[0].get("mode") not in {"success", "error"}:
        raise ValueError("Need exactly one registered WorkBuddy run with a supported fixture mode")
    fixture_name = protocol.get("fixture_file", BASE + "/fixture.json")
    if fixture_name not in files or "scripts/controlled_probe_mcp.py" not in files:
        raise ValueError("Registration must bind both fixture and shared MCP source")
    fixture = read(safe_relative(root, fixture_name))
    arguments = fixture.get("arguments")
    if (not isinstance(arguments, dict) or set(arguments) != {"text", "destination"}
            or not isinstance(arguments["text"], str) or arguments["destination"] != "artifact.txt"):
        raise ValueError("Unexpected fixed tool arguments")
    committed_at = subprocess.check_output(["git", "show", "-s", "--format=%cI", commit], cwd=root,
                                          text=True).strip()
    if instant(committed_at) > instant(now()):
        raise ValueError("Registration commit is in the future")
    return protocol, matching[0], fixture, {"path": relative, "sha256": digest(protocol_bytes),
                                         "committed_at": committed_at}


def wait_for_operator(evidence, host_started_at, request_count, *, prepare_seconds=PREPARE_SECONDS,
                      timeout_seconds=TASK_SECONDS, poll_seconds=0.1,
                      monotonic=time.monotonic, sleep=time.sleep, current_time=now):
    """Wait on explicit operator records; two HTTP requests never imply completion."""
    prepare_deadline = monotonic() + prepare_seconds
    deadline = None
    submission = None
    observed_at = None
    requests_before_submission = None
    while True:
        submission_path = evidence / "submission.json"
        if submission is None and submission_path.exists():
            candidate = read(submission_path)
            if (not isinstance(candidate, dict) or candidate.get("actual_submitted") is not True
                    or candidate.get("method") != "native_computer_use"):
                raise ValueError("Submission must record an actual native Computer Use submission")
            submitted = instant(candidate["at"])
            observed_at = current_time()
            observed = instant(observed_at)
            if submitted < instant(host_started_at) or (submitted - observed).total_seconds() > 1:
                raise ValueError("Submission timestamp is outside the host observation interval")
            # Use a monotonic deadline after deducting any delay between the real
            # submission and this process observing the operator's receipt.
            delay = max(0.0, (observed - submitted).total_seconds())
            deadline = monotonic() + max(0.0, timeout_seconds - delay)
            submission = candidate
            requests_before_submission = request_count()
        if (evidence / "stop.json").exists():
            stop = read(evidence / "stop.json")
            if not isinstance(stop, dict):
                raise ValueError("Operator stop record must be an object")
            return {"stop_basis": "operator_stop", "operator_stop": stop, "submission": submission,
                    "submission_observed_at": observed_at, "deadline_expired": False,
                    "requests_before_submission_observed": requests_before_submission}
        if deadline is not None and monotonic() >= deadline:
            return {"stop_basis": "task_deadline_expired", "operator_stop": None, "submission": submission,
                    "submission_observed_at": observed_at, "deadline_expired": True,
                    "requests_before_submission_observed": requests_before_submission}
        if deadline is None and monotonic() >= prepare_deadline:
            return {"stop_basis": "preparation_deadline_expired", "operator_stop": None, "submission": None,
                    "submission_observed_at": None, "deadline_expired": False,
                    "requests_before_submission_observed": None}
        sleep(poll_seconds)


def collect_artifact(workspace, evidence):
    source = workspace / "artifact.txt"
    try:
        info = source.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
        raise ValueError("Artifact must be a regular file, not a link or reparse point")
    data = source.read_bytes()
    destination = evidence / "collected"
    destination.mkdir(exist_ok=False)
    with (destination / "artifact.txt").open("xb") as stream:
        stream.write(data)
    return {"bytes": len(data), "sha256": digest(data), "acquired_at": now(),
            "source_stable_during_copy": source.read_bytes() == data}


def serve_run(run_id, phase, registration, *, repo_root=ROOT, work_root=WORK, private_root=None,
              poll_seconds=0.1):
    repo_root, work_root = Path(repo_root), Path(work_root)
    private_root = Path(private_root) if private_root is not None else repo_root / "private/controlled-workbuddy-v1"
    protocol, spec, fixture, registration_receipt = verify_registration(repo_root, run_id, phase, registration)
    runroot, evidence = work_root / run_id, private_root / run_id
    if runroot.exists() or evidence.exists():
        raise FileExistsError("Refusing to overwrite an existing run or evidence directory")
    runroot.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    runroot.mkdir(exist_ok=False)
    evidence.mkdir(exist_ok=False)
    workspace, runtime = runroot / "work", runroot / "runtime"
    workspace.mkdir(exist_ok=False)
    runtime.mkdir(exist_ok=False)
    tool = runtime / "controlled_probe_mcp.py"
    shutil.copyfile(repo_root / "scripts/controlled_probe_mcp.py", tool)
    host_started_at = now()
    started_mono = time.monotonic()
    result = {"run_id": run_id, "phase": phase, "product_id": "workbuddy", "mode": spec["mode"],
              "registration_commit": registration, "registration_file": Path(registration_receipt["path"]).name,
              "registration_receipt": registration_receipt, "host_started_at": host_started_at,
              "started_at": None, "timeout_seconds": TASK_SECONDS, "preparation_timeout_seconds": PREPARE_SECONDS,
              "model_kind": "deterministic_local_transport_fixture", "real_model_inference": False,
              "version": UI_VERSION, "version_basis": "operator UI label; fixture host does not query the product",
              "shared_tool_sha256": digest(tool.read_bytes()),
              "frozen_arguments_sha256": digest(encoded(fixture["arguments"])),
              "actual_submitted": False, "artifact": None, "runtime_errors": [],
              "deadline_expired": False, "stop_basis": None, "initial_workspace_inventory": [],
              "native_completion": "unknown; must be established by operator observations"}
    state = None
    try:
        with FixtureServer(fixture["arguments"], evidence / "model-events.jsonl") as server:
            state = server.state
            mcp_args = [str(tool), "--workspace", str(workspace), "--mode", spec["mode"],
                        "--journal", str(evidence / "mcp-events.jsonl")]
            ready = {"run_id": run_id, "phase": phase, "mode": spec["mode"], "product_id": "workbuddy",
                     "host_started_at": host_started_at, "base_url": server.base_url,
                     "chat_url": server.base_url + "/chat/completions", "python": sys.executable,
                     "mcp_command": sys.executable, "mcp_args": mcp_args, "mcp_server_name": "contract",
                     "mcp_tool_name": "mcp__contract__probe_commit", "workspace": str(workspace),
                     "runroot": str(runroot), "runtime": str(runtime), "evidence": str(evidence),
                     "version": UI_VERSION, "shared_tool_sha256": result["shared_tool_sha256"],
                     "submission_file": str(evidence / "submission.json"), "stop_file": str(evidence / "stop.json"),
                     "timeout_seconds": TASK_SECONDS, "preparation_timeout_seconds": PREPARE_SECONDS,
                     "real_model_inference": False, "product_process_started_by_host": False}
            save_new(evidence / "ready.json", ready)
            print(json.dumps({"ready": str(evidence / "ready.json"), "chat_url": ready["chat_url"]}), flush=True)
            observation = wait_for_operator(evidence, host_started_at, lambda: state.requests,
                                            poll_seconds=poll_seconds)
            result.update({key: value for key, value in observation.items() if key != "submission"})
            if observation["submission"] is not None:
                result["actual_submitted"] = True
                result["started_at"] = observation["submission"]["at"]
    except KeyboardInterrupt:
        result["stop_basis"] = "host_keyboard_interrupt"
        result["runtime_errors"].append({"type": "KeyboardInterrupt", "message": "Fixture host interrupted"})
    except Exception as error:
        result["stop_basis"] = "host_runtime_error"
        result["runtime_errors"].append({"type": type(error).__name__, "message": str(error)})
    finally:
        # Preserve a valid actual submission even when subsequent operator data
        # or server shutdown failed before wait_for_operator returned.
        if not result["actual_submitted"] and (evidence / "submission.json").is_file():
            try:
                submission = read(evidence / "submission.json")
                if (submission.get("actual_submitted") is True and submission.get("method") == "native_computer_use"
                        and instant(host_started_at) <= instant(submission["at"]) <= instant(now())):
                    result["actual_submitted"] = True
                    result["started_at"] = submission["at"]
            except (OSError, ValueError, KeyError, AttributeError):
                pass
        try:
            result["artifact"] = collect_artifact(workspace, evidence)
        except Exception as error:
            result["runtime_errors"].append({"type": type(error).__name__, "message": str(error)})
        result["local_model_requests"] = state.requests if state is not None else 0
        result["ended_at"] = now()
        result["host_elapsed_seconds"] = time.monotonic() - started_mono
        result["elapsed_seconds"] = ((instant(result["ended_at"]) - instant(result["started_at"])).total_seconds()
                                     if result["started_at"] else None)
        result["mcp_journal_present"] = (evidence / "mcp-events.jsonl").is_file()
        result["product_process_started_by_host"] = False
        result["product_stop_performed_by_host"] = False
        result["deadline_limitation"] = "Deadline expiry closes this HTTP fixture only; the operator must stop the desktop task."
        save_new(evidence / "execution.json", result)
    print(json.dumps({"run_id": run_id, "stop_basis": result["stop_basis"],
                      "actual_submitted": result["actual_submitted"], "local_model_requests": result["local_model_requests"],
                      "runtime_error_count": len(result["runtime_errors"])}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", choices=("calibration", "main"), required=True)
    parser.add_argument("--registration", required=True)
    args = parser.parse_args()
    result = serve_run(args.run_id, args.phase, args.registration)
    return 1 if result["runtime_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
