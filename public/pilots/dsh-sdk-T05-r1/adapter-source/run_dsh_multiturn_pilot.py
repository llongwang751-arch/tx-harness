"""Real T04 SDK pilot, with one process and one session across both turns.

This speaks the documented rc.2 JSON-RPC protocol. It does not read credentials,
repair outputs, or change persistent product settings. Full wire logs are private.
An operator can record an observed semantic request in release-decision.json;
otherwise the preregistered fixture is released at 120 seconds.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import uuid

from run_dsh_pilot import ROOT, digest, inventory


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def project(event):
    """Only externally observable committed text/tools, never hidden context."""
    kind = event.get("type")
    data = event.get("data", {})
    if kind == "assistant/message":
        return {"type": "text", "text": "\n".join(
            b.get("text", "") for b in data.get("message", {}).get("content", [])
            if b.get("type") == "text")}
    if kind == "tool/call":
        arguments = data.get("arguments", "")
        try:
            arguments = json.loads(arguments) if arguments else {}
        except (ValueError, TypeError):
            pass
        return {"type": "tool_call", "callId": data.get("callId"),
                "tool": data.get("name"), "input": arguments}
    if kind == "tool/result" and event.get("surfaceOp") == "append":
        message = data.get("message", {})
        return {"type": "tool_result", "callId": message.get("toolCallId"),
                "status": "error" if message.get("isError") else "completed",
                "result": "".join(b.get("text", "") for b in message.get("content", [])
                                  if b.get("type") == "text")}
    if kind in ("turn/start", "turn/end", "step/start", "step/end"):
        return {"type": "status", "phase": kind.replace("/", "_"),
                **{k: data[k] for k in ("turn", "step", "reason") if k in data}}
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--participant-root", type=Path, default=Path("D:/harness-participants"))
    args = parser.parse_args()
    if args.replicate < 1 or not 120 <= args.timeout_seconds <= 1200:
        parser.error("positive replicate and timeout between 120 and 1200 seconds required")
    participant_root = args.participant_root.resolve()
    if participant_root == ROOT or participant_root.is_relative_to(ROOT):
        parser.error("participant workspace must be outside evaluator repository")
    name = f"dsh-T04-r{args.replicate}"
    workspace = participant_root / f"pilot-{name}"
    private = ROOT / "private/pilots" / name
    case_dir = ROOT / "cases/T04"
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    protocol = case["release_protocol"]
    install = Path(os.environ["LOCALAPPDATA"]) / "Programs/DeepSeek Harness"
    executable = install / "DeepSeek Harness.exe"
    cli = install / "resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js"
    patch = private / "one-run.patch.yml"
    command = [str(executable), "--expose-internals", str(cli), "--patch", str(patch),
               "--profile", "sdk"]
    metadata = {"product": "dsh", "surface": "desktop-bundled CLI", "profile": "sdk",
                "track": "pilot", "case": "T04", "replicate": args.replicate,
                "installation_version": "0.2.0-rc.2", "command": command,
                "workspace": str(workspace), "private_logs": str(private),
                "requested_provider": "deepseek-account", "requested_model": "deepseek-flash",
                "requested_reasoning_effort": "high", "timeout_seconds": args.timeout_seconds,
                "release_deadline_seconds": 120, "manual_interventions": 0}
    if not args.execute:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return
    if workspace.exists() or private.exists():
        raise SystemExit("Refusing overwrite of existing workspace or evidence")
    workspace.mkdir(parents=True)
    private.mkdir(parents=True)
    shutil.copytree(case_dir / "inputs", workspace / "inputs")
    (workspace / "outputs").mkdir()
    prompt = (case_dir / "prompt.md").read_text(encoding="utf-8") + \
        "\n\n将交付文件写入 outputs/，不要修改 inputs/。\n"
    (workspace / "prompt.md").write_text(prompt, encoding="utf-8")
    (private / "submitted-prompt.md").write_text(prompt, encoding="utf-8")
    patch.write_text(
        "- id: skill-filesystem\n  config:\n    includeDefaultRoots: false\n"
        "    watch: false\n    bundledSkillDir: " +
        json.dumps(str(install / "resources/runtime/office-skills").replace("\\", "/"),
                   ensure_ascii=False) +
        "\n- id: tool-web\n  disabled: true\n", encoding="utf-8")
    metadata.update({"initial_files": inventory(workspace), "patch_sha256": digest(patch),
                     "runner_sha256": digest(Path(__file__)),
                     "session_id": "pilot-dsh-T04-" + str(uuid.uuid4()),
                     "sandbox": "workspace-write", "task_network_tool": "disabled",
                     "skills": "user/project roots disabled; product bundled Office skills retained",
                     "runtime_started_at": now(), "state": "initializing"})
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    env["DSH_PERMISSION_MODE"] = "workspace-write"
    save(private / "run.json", metadata)
    events = queue.Queue()
    process = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    metadata["pid"] = process.pid
    save(private / "run.json", metadata)
    log_lock = threading.Lock()
    received = (private / "received.jsonl").open("w", encoding="utf-8")
    sent = (private / "sent.jsonl").open("w", encoding="utf-8")
    visible = (private / "visible-parent-events.jsonl").open("w", encoding="utf-8")

    def collect(pipe, stream):
        with (private / f"{stream}.raw").open("wb") as raw:
            for number, line in enumerate(iter(pipe.readline, b""), 1):
                raw.write(line)
                raw.flush()
                record = {"received_at": now(), "stream": stream, "line_number": number,
                          "line": line.decode("utf-8", errors="replace").rstrip("\r\n")}
                with log_lock:
                    received.write(json.dumps(record, ensure_ascii=False) + "\n")
                    received.flush()
                if stream == "stdout":
                    try:
                        events.put((json.loads(record["line"]), record["received_at"], number))
                    except ValueError:
                        events.put(({"invalid_frame": True}, record["received_at"], number))
        events.put(({"eof": stream}, now(), None))

    threads = [threading.Thread(target=collect, args=(process.stdout, "stdout")),
               threading.Thread(target=collect, args=(process.stderr, "stderr"))]
    for thread in threads:
        thread.start()
    counter = 0
    responses = {}
    parent_status = None
    end_turns = []
    texts_by_line = {}

    def send(method, params=None):
        nonlocal counter
        counter += 1
        message = {"jsonrpc": "2.0", "id": counter, "method": method}
        if params is not None:
            message["params"] = params
        timestamp = now()
        sent.write(json.dumps({"sent_at": timestamp, "frame": message}, ensure_ascii=False) + "\n")
        sent.flush()
        process.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
        process.stdin.flush()
        return counter, timestamp

    def consume(timeout=0.1):
        nonlocal parent_status
        try:
            frame, timestamp, number = events.get(timeout=timeout)
        except queue.Empty:
            return
        if "id" in frame:
            responses[frame["id"]] = frame
        params = frame.get("params", {})
        if params.get("sessionId") != metadata["session_id"]:
            return
        if frame.get("method") == "session.status":
            parent_status = params.get("status")
        if frame.get("method") == "session.event":
            event = params.get("event", {})
            if event.get("type") == "turn/end":
                end_turns.append({"received_at": timestamp, "source_stdout_line": number,
                                  "reason": event.get("data", {}).get("reason")})
            projected = project(event)
            if projected is not None:
                item = {"received_at": timestamp, "source_stdout_line": number,
                        "event": projected}
                visible.write(json.dumps(item, ensure_ascii=False) + "\n")
                visible.flush()
                if projected["type"] == "text" and projected["text"]:
                    texts_by_line[number] = item

    def await_response(request, deadline):
        while request not in responses:
            if process.poll() is not None:
                raise RuntimeError("SDK process exited before its requested receipt")
            if time.monotonic() >= deadline:
                raise TimeoutError("SDK receipt timeout")
            consume()
        response = responses[request]
        if "error" in response:
            save(private / f"rpc-error-{request}.json", response)
            raise RuntimeError(f"SDK request {request} returned JSON-RPC error")
        return response["result"]

    task_started = None
    try:
        request, _ = send("initialize", {"cwd": str(workspace), "provider": "deepseek-account",
                                       "model": "deepseek-flash", "reasoningEffort": "high"})
        metadata["initialize_result"] = await_response(request, time.monotonic() + 120)
        task_started = time.monotonic()
        request, metadata["started_at"] = send("session/prompt", {
            "sessionId": metadata["session_id"], "contentBlocks": [{"type": "text", "text": prompt}]})
        deadline = task_started + args.timeout_seconds
        metadata["initial_prompt_receipt"] = await_response(request, deadline)
        metadata["state"] = "observing_missing-input_request"
        save(private / "run.json", metadata)
        released = False
        release_request = None
        while time.monotonic() < deadline:
            consume()
            elapsed = time.monotonic() - task_started
            decision_path = private / "release-decision.json"
            decision = None
            if not released and decision_path.is_file():
                decision = json.loads(decision_path.read_text(encoding="utf-8"))
                number = decision.get("source_stdout_line")
                observed = texts_by_line.get(number)
                if decision.get("mode") != "active" or observed is None or \
                        not decision.get("request_text") or \
                        decision["request_text"] not in observed["event"]["text"]:
                    raise RuntimeError("Active release requires an actually observed committed request")
                if elapsed >= 120:
                    decision = None
            if not released and (decision is not None or elapsed >= 120):
                mode = "active" if decision is not None else "passive"
                source = case_dir / protocol["release_files"][0]["source"]
                destination = workspace / "inputs/rates.json"
                outputs_before = inventory(workspace / "outputs")
                shutil.copyfile(source, destination)
                release = {"mode": mode, "file_provided_at": now(),
                           "seconds_since_initial_prompt": round(time.monotonic() - task_started, 3),
                           "file": "inputs/rates.json", "sha256": digest(destination),
                           "source_sha256": digest(source), "outputs_before_release": outputs_before,
                           "response_text": protocol["response_text"],
                           "observed_request": decision}
                release_request, release["message_sent_at"] = send("session/prompt", {
                    "sessionId": metadata["session_id"],
                    "contentBlocks": [{"type": "text", "text": protocol["response_text"]}]})
                metadata["release"] = release
                save(private / "release.json", release)
                metadata["state"] = "running_recovery_same_session"
                save(private / "run.json", metadata)
                released = True
            if released and release_request in responses:
                response = responses[release_request]
                if "error" in response:
                    raise RuntimeError("Supplement prompt was rejected by SDK")
                metadata["supplement_prompt_receipt"] = response["result"]
                if len(end_turns) >= 2 and parent_status == "idle":
                    metadata["state"] = "completed_observed_interval"
                    metadata["timed_out"] = False
                    break
            if process.poll() is not None:
                raise RuntimeError("SDK runtime exited during the task interval")
        else:
            metadata["state"] = "timeout"
            metadata["timed_out"] = True
        metadata["finished_at"] = now()
        metadata["elapsed_seconds"] = round(time.monotonic() - task_started, 3)
        metadata["parent_turn_ends"] = end_turns
        metadata["final_files"] = inventory(workspace)
        metadata["outputs"] = inventory(workspace / "outputs")
        save(private / "run.json", metadata)
        request, metadata["shutdown_sent_at"] = send("shutdown")
        metadata["shutdown_result"] = await_response(request, time.monotonic() + 15)
        process.stdin.close()
        process.wait(timeout=30)
    except Exception as error:
        metadata["adapter_error"] = f"{type(error).__name__}: {error}"
        metadata["finished_at"] = now()
        metadata["elapsed_seconds"] = round(time.monotonic() - task_started, 3) \
            if task_started is not None else None
        metadata["final_files"] = inventory(workspace)
        metadata["outputs"] = inventory(workspace / "outputs")
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        metadata["adapter_forced_termination"] = True
    finally:
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            metadata["adapter_forced_termination"] = True
        for thread in threads:
            thread.join(timeout=15)
        metadata["exit_code"] = process.poll()
        metadata["runtime_finished_at"] = now()
        save(private / "run.json", metadata)
        received.close()
        sent.close()
        visible.close()
    print(json.dumps({key: metadata.get(key) for key in
                     ("product", "case", "workspace", "state", "elapsed_seconds",
                      "exit_code", "timed_out", "outputs", "adapter_error")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
