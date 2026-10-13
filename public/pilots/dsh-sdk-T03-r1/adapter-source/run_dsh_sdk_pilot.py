"""Run one real DSH SDK pilot for T01..T05; dry-run unless --execute.

The original T04 runner stays unchanged. All new directories include `dsh-sdk`.
T04 keeps the same two-turn release contract; other cases use one native turn.
Raw wire logs include hidden context and must remain private.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import uuid

from run_dsh_multiturn_pilot import now, project, save
from run_dsh_pilot import ROOT, digest, inventory


class SdkPeer:
    """Only the documented initialize/session-prompt/shutdown JSON-RPC methods."""

    def __init__(self, process, private, session_id):
        self.process, self.private, self.session_id = process, private, session_id
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.received = (private / "received.jsonl").open("w", encoding="utf-8")
        self.sent = (private / "sent.jsonl").open("w", encoding="utf-8")
        self.visible = (private / "visible-parent-events.jsonl").open("w", encoding="utf-8")
        self.counter, self.status = 0, None
        self.responses, self.texts, self.ends = {}, {}, []
        self.threads = [threading.Thread(target=self.collect, args=(process.stdout, "stdout")),
                        threading.Thread(target=self.collect, args=(process.stderr, "stderr"))]
        for thread in self.threads:
            thread.start()

    def collect(self, pipe, stream):
        with (self.private / f"{stream}.raw").open("wb") as raw:
            for number, line in enumerate(iter(pipe.readline, b""), 1):
                raw.write(line)
                raw.flush()
                record = {"received_at": now(), "stream": stream, "line_number": number,
                          "line": line.decode("utf-8", errors="replace").rstrip("\r\n")}
                with self.lock:
                    self.received.write(json.dumps(record, ensure_ascii=False) + "\n")
                    self.received.flush()
                if stream == "stdout":
                    try:
                        self.queue.put((json.loads(record["line"]), record["received_at"], number))
                    except ValueError:
                        self.queue.put(({"invalid_frame": True}, record["received_at"], number))

    def send(self, method, params=None):
        self.counter += 1
        frame = {"jsonrpc": "2.0", "id": self.counter, "method": method}
        if params is not None:
            frame["params"] = params
        timestamp = now()
        self.sent.write(json.dumps({"sent_at": timestamp, "frame": frame}, ensure_ascii=False) + "\n")
        self.sent.flush()
        self.process.stdin.write((json.dumps(frame, ensure_ascii=False) + "\n").encode("utf-8"))
        self.process.stdin.flush()
        return self.counter, timestamp

    def consume(self, timeout=0.1):
        try:
            frame, timestamp, number = self.queue.get(timeout=timeout)
        except queue.Empty:
            return
        if "id" in frame:
            self.responses[frame["id"]] = frame
        params = frame.get("params", {})
        if params.get("sessionId") != self.session_id:
            return
        if frame.get("method") == "session.status":
            self.status = params.get("status")
        if frame.get("method") == "session.event":
            event = params.get("event", {})
            if event.get("type") == "turn/end":
                self.ends.append({"received_at": timestamp, "source_stdout_line": number,
                                  "reason": event.get("data", {}).get("reason")})
            visible = project(event)
            if visible is not None:
                item = {"received_at": timestamp, "source_stdout_line": number, "event": visible}
                self.visible.write(json.dumps(item, ensure_ascii=False) + "\n")
                self.visible.flush()
                if visible["type"] == "text" and visible["text"]:
                    self.texts[number] = item

    def response(self, request, deadline):
        while request not in self.responses:
            if self.process.poll() is not None:
                raise RuntimeError("SDK process exited before its requested receipt")
            if time.monotonic() >= deadline:
                raise TimeoutError("SDK receipt timeout")
            self.consume()
        frame = self.responses[request]
        if "error" in frame:
            save(self.private / f"rpc-error-{request}.json", frame)
            raise RuntimeError(f"SDK request {request} returned JSON-RPC error")
        return frame["result"]

    def close_logs(self):
        for thread in self.threads:
            thread.join(timeout=15)
        self.received.close()
        self.sent.close()
        self.visible.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--case", choices=["T01", "T02", "T03", "T04", "T05"], default="T04")
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--participant-root", type=Path, default=Path("D:/harness-participants"))
    parser.add_argument("--concurrency-group", default="none")
    parser.add_argument("--concurrency-max", type=int, default=1)
    args = parser.parse_args()
    if args.replicate < 1 or not 120 <= args.timeout_seconds <= 1200 or args.concurrency_max < 1:
        parser.error("positive replicate/concurrency and timeout between 120 and 1200 required")
    participant_root = args.participant_root.resolve()
    if participant_root == ROOT or participant_root.is_relative_to(ROOT):
        parser.error("participant workspace must be outside the evaluator repository")
    name = f"dsh-sdk-{args.case}-r{args.replicate}"
    workspace = participant_root / f"pilot-{name}"
    private = ROOT / "private/pilots" / name
    case_dir = ROOT / "cases" / args.case
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    protocol = case.get("release_protocol")
    install = Path(os.environ["LOCALAPPDATA"]) / "Programs/DeepSeek Harness"
    executable = install / "DeepSeek Harness.exe"
    cli = install / "resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js"
    patch = private / "one-run.patch.yml"
    command = [str(executable), "--expose-internals", str(cli), "--patch", str(patch), "--profile", "sdk"]
    metadata = {"product": "dsh", "surface": "desktop-bundled CLI", "profile": "sdk",
                "track": "pilot", "case": args.case, "replicate": args.replicate,
                "installation_version": "0.2.0-rc.2", "command": command,
                "workspace": str(workspace), "private_logs": str(private),
                "requested_provider": "deepseek-account", "requested_model": "deepseek-flash",
                "requested_reasoning_effort": "high", "timeout_seconds": args.timeout_seconds,
                "release_deadline_seconds": 120 if protocol else None, "manual_interventions": 0,
                "concurrency": {"group": args.concurrency_group, "maximum": args.concurrency_max,
                                "same_product_account": True,
                                "timing_limitation": "May include shared account/service/CPU contention; not a single-task speed comparison"}}
    if not args.execute:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return
    if workspace.exists() or private.exists():
        raise SystemExit("Refusing overwrite of existing workspace or evidence")
    workspace.mkdir(parents=True)
    private.mkdir(parents=True)
    shutil.copytree(case_dir / case["input_dir"], workspace / "inputs")
    (workspace / "outputs").mkdir()
    prompt = (case_dir / case["prompt_file"]).read_text(encoding="utf-8") + \
        "\n\n将交付文件写入 outputs/，不要修改 inputs/。\n"
    (workspace / "prompt.md").write_text(prompt, encoding="utf-8")
    (private / "submitted-prompt.md").write_text(prompt, encoding="utf-8")
    # Snapshot the exact adapter and its shared helpers without giving these to the product.
    source_snapshot = private / "adapter-source"
    source_snapshot.mkdir()
    dependencies = [Path(__file__), ROOT / "scripts/run_dsh_multiturn_pilot.py",
                    ROOT / "scripts/run_dsh_pilot.py"]
    for source in dependencies:
        shutil.copyfile(source, source_snapshot / source.name)
    patch.write_text(
        "- id: skill-filesystem\n  config:\n    includeDefaultRoots: false\n"
        "    watch: false\n    bundledSkillDir: " +
        json.dumps(str(install / "resources/runtime/office-skills").replace("\\", "/"), ensure_ascii=False) +
        "\n- id: tool-web\n  disabled: true\n", encoding="utf-8")
    metadata.update({"initial_files": inventory(workspace), "patch_sha256": digest(patch),
                     "runner_sha256": digest(Path(__file__)),
                     "adapter_dependency_sha256": {s.name: digest(s) for s in dependencies},
                     "session_id": f"pilot-dsh-sdk-{args.case}-" + str(uuid.uuid4()),
                     "sandbox": "workspace-write", "task_network_tool": "disabled",
                     "skills": "user/project roots disabled; product bundled Office skills retained",
                     "runtime_started_at": now(), "state": "initializing"})
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    env["DSH_PERMISSION_MODE"] = "workspace-write"
    save(private / "run.json", metadata)
    process = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    metadata["pid"] = process.pid
    save(private / "run.json", metadata)
    peer = SdkPeer(process, private, metadata["session_id"])
    started = None
    try:
        request, _ = peer.send("initialize", {"cwd": str(workspace), "provider": "deepseek-account",
                                            "model": "deepseek-flash", "reasoningEffort": "high"})
        metadata["initialize_result"] = peer.response(request, time.monotonic() + 120)
        started = time.monotonic()
        request, metadata["started_at"] = peer.send("session/prompt", {
            "sessionId": metadata["session_id"], "contentBlocks": [{"type": "text", "text": prompt}]})
        deadline = started + args.timeout_seconds
        metadata["initial_prompt_receipt"] = peer.response(request, deadline)
        metadata["state"] = "observing_missing-input_request" if protocol else "running_task"
        save(private / "run.json", metadata)
        released, release_request = False, None
        while time.monotonic() < deadline:
            peer.consume()
            elapsed = time.monotonic() - started
            decision = None
            decision_path = private / "release-decision.json"
            if protocol and not released and decision_path.is_file():
                decision = json.loads(decision_path.read_text(encoding="utf-8"))
                observed = peer.texts.get(decision.get("source_stdout_line"))
                if decision.get("mode") != "active" or observed is None or not decision.get("request_text") \
                        or decision["request_text"] not in observed["event"]["text"]:
                    raise RuntimeError("Active release requires an actually observed committed request")
                if elapsed >= 120:
                    decision = None
            if protocol and not released and (decision is not None or elapsed >= 120):
                source = case_dir / protocol["release_files"][0]["source"]
                destination = workspace / "inputs/rates.json"
                # Keep a byte-exact pre-release snapshot for subsequent multi-turn pilots.
                shutil.copytree(workspace / "outputs", private / "outputs-before-release")
                before = inventory(workspace / "outputs")
                shutil.copyfile(source, destination)
                release = {"mode": "active" if decision is not None else "passive",
                           "file_provided_at": now(), "seconds_since_initial_prompt": round(time.monotonic() - started, 3),
                           "file": "inputs/rates.json", "sha256": digest(destination), "source_sha256": digest(source),
                           "outputs_before_release": before, "response_text": protocol["response_text"],
                           "observed_request": decision}
                release_request, release["message_sent_at"] = peer.send("session/prompt", {
                    "sessionId": metadata["session_id"],
                    "contentBlocks": [{"type": "text", "text": protocol["response_text"]}]})
                metadata["release"] = release
                metadata["state"] = "running_recovery_same_session"
                save(private / "release.json", release)
                save(private / "run.json", metadata)
                released = True
            if released and release_request in peer.responses:
                if "error" in peer.responses[release_request]:
                    raise RuntimeError("SDK rejected supplementary prompt")
                metadata["supplement_prompt_receipt"] = peer.responses[release_request]["result"]
            needed_turns = 2 if protocol else 1
            supplement_accepted = not protocol or metadata.get("supplement_prompt_receipt") is not None
            if supplement_accepted and len(peer.ends) >= needed_turns and peer.status == "idle":
                metadata["state"] = "completed_observed_interval"
                metadata["timed_out"] = False
                break
            if process.poll() is not None:
                raise RuntimeError("SDK runtime exited during the observed interval")
        else:
            metadata["state"], metadata["timed_out"] = "timeout", True
        metadata["finished_at"] = now()
        metadata["elapsed_seconds"] = round(time.monotonic() - started, 3)
        metadata["parent_turn_ends"] = peer.ends
        metadata["final_files"] = inventory(workspace)
        metadata["outputs"] = inventory(workspace / "outputs")
        save(private / "run.json", metadata)
        request, metadata["shutdown_sent_at"] = peer.send("shutdown")
        metadata["shutdown_result"] = peer.response(request, time.monotonic() + 15)
        process.stdin.close()
        process.wait(timeout=30)
    except Exception as error:
        metadata["adapter_error"] = f"{type(error).__name__}: {error}"
        metadata["finished_at"] = now()
        metadata["elapsed_seconds"] = round(time.monotonic() - started, 3) if started else None
        metadata["parent_turn_ends"] = peer.ends
        metadata["final_files"] = inventory(workspace)
        metadata["outputs"] = inventory(workspace / "outputs")
    finally:
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            metadata["adapter_forced_termination"] = True
        peer.close_logs()
        metadata["exit_code"] = process.poll()
        metadata["runtime_finished_at"] = now()
        save(private / "run.json", metadata)
    print(json.dumps({k: metadata.get(k) for k in
                     ("product", "case", "workspace", "state", "elapsed_seconds", "exit_code",
                      "timed_out", "outputs", "adapter_error")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
