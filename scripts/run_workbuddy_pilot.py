"""Run a real installed WorkBuddy embedded-CLI pilot; never synthesize results.

Raw streams are private. This is an exploratory CLI entrypoint, not a claim of
desktop parity or OS-level isolation. No evaluator/protocol files are changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[1]
NODE = Path.home() / ".workbuddy/binaries/node/versions/22.22.2-6/node.exe"
CLI = Path("E:/workbuddy/resources/app.asar.unpacked/cli/bin/codebuddy")
TOOLS = "Read,Write,Edit,Glob,Grep"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inventory(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def command(session_id, evidence, setting_sources):
    return [str(NODE), str(CLI), "--print", "--verbose", "--output-format", "stream-json",
            "--input-format", "text", "--session-id", session_id,
            "--no-session-persistence", "--setting-sources", setting_sources,
            "--settings", str(evidence / "process-settings.json"),
            "--strict-mcp-config", "--mcp-config", str(evidence / "empty-mcp.json"),
            "--tools", TOOLS, "--allowedTools", TOOLS, "--permission-mode", "acceptEdits"]


def capture(pipe, raw_path, receipt_path, stream, started):
    with raw_path.open("wb") as raw, receipt_path.open("w", encoding="utf-8") as receipts:
        offset = 0
        while True:
            chunk = pipe.readline()
            if not chunk:
                break
            raw.write(chunk)
            raw.flush()
            receipts.write(json.dumps({"at": stamp(), "elapsed_seconds": time.monotonic() - started,
                                       "stream": stream, "offset": offset,
                                       "length": len(chunk)}) + "\n")
            receipts.flush()
            offset += len(chunk)


def extract_observations(raw_path):
    """Only summaries; do not publish raw thinking/system/authentication fields."""
    parsed, unparsed, types, tools, model_metadata = 0, 0, {}, [], []
    final = []
    for line in raw_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            unparsed += 1
            continue
        if not isinstance(event, dict):
            continue
        parsed += 1
        kind = str(event.get("type", "unknown"))
        types[kind] = types.get(kind, 0) + 1
        if kind == "system" and event.get("subtype") == "init":
            model_metadata.append({k: event[k] for k in ("model", "permissionMode", "tools", "version", "cwd")
                                   if k in event})
        message = event.get("message", {})
        if isinstance(message, dict):
            if message.get("model"):
                model_metadata.append({"message_model": message["model"]})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool = {"name": block.get("name"), "id": block.get("id")}
                        tool_input = block.get("input", {})
                        if isinstance(tool_input, dict):
                            tool["file_path"] = tool_input.get("file_path")
                        tools.append(tool)
        if kind == "result":
            final.append({k: event[k] for k in ("subtype", "is_error", "result", "duration_ms", "num_turns")
                          if k in event})
    return {"parsed_events": parsed, "unparsed_lines": unparsed, "event_types": types,
            "model_metadata": model_metadata, "tool_calls": tools, "result_events": final}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="T01", choices=["T01", "T02", "T03", "T05"])
    parser.add_argument("--replicate", default=1, type=int)
    parser.add_argument("--participant-root", default="D:/harness-participants", type=Path)
    parser.add_argument("--evidence-root", default=str(ROOT / "private/pilots"), type=Path)
    parser.add_argument("--timeout", default=1200, type=float)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--setting-sources", default="none", choices=["none", "user,project,local"])
    opts = parser.parse_args()
    if not 0 < opts.timeout <= 1200:
        raise ValueError("Pilot timeout must be in (0,1200].")
    run_id = f"workbuddy-{opts.case}-r{opts.replicate}"
    workspace = opts.participant_root.resolve() / f"pilot-{run_id}"
    evidence = opts.evidence_root.resolve() / run_id
    if workspace.is_relative_to(ROOT) or ROOT.is_relative_to(workspace):
        raise ValueError("Participant workspace must be outside the evaluator repository.")
    session_id = str(uuid.uuid4())
    args = command(session_id, evidence, opts.setting_sources)
    plan = {"run_id": run_id, "participant_workspace": str(workspace), "evidence_directory": str(evidence),
            "entrypoint": "WorkBuddy installed embedded CLI/headless exploratory pilot",
            "command": args, "model_requested": None, "timeout_seconds": opts.timeout,
            "setting_sources_requested": opts.setting_sources,
            "skills_policy": "Skill absent from requested tool subset; effective restriction and built-in prompt content not proven absent",
            "isolation": "Fresh external cwd; file tools only. No OS sandbox is asserted.",
            "formal_sample": False}
    if not opts.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if workspace.exists() or evidence.exists():
        raise FileExistsError("Existing participant/evidence directory; refuse overwrite or selective rerun.")
    if not NODE.is_file() or not CLI.is_file():
        raise FileNotFoundError("Installed WorkBuddy runtime or CLI missing")
    case_dir = ROOT / "cases" / opts.case
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
    workspace.mkdir(parents=True)
    evidence.mkdir(parents=True)
    shutil.copytree(case_dir / "inputs", workspace / "inputs")
    shutil.copyfile(case_dir / "prompt.md", workspace / "prompt.md")
    (workspace / "outputs").mkdir()
    write_json(evidence / "empty-mcp.json", {"mcpServers": {}})
    write_json(evidence / "process-settings.json", {"disableAllHooks": True})
    write_json(evidence / "plan.json", plan)
    write_json(evidence / "adapter-provenance.json", {"sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                                     "path": "scripts/run_workbuddy_pilot.py"})
    initial = inventory(workspace)
    write_json(evidence / "initial-inventory.json", initial)
    versions = {}
    for label, version_args in (("node", [str(NODE), "--version"]),
                                ("cli", [str(NODE), str(CLI), "--version"])):
        ver = subprocess.run(version_args, capture_output=True, timeout=30,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        versions[label] = {"exit_code": ver.returncode, "stdout": ver.stdout.decode("utf-8", "replace").strip()}
    write_json(evidence / "versions.json", versions)
    original_prompt = (workspace / "prompt.md").read_text(encoding="utf-8-sig")
    prompt = original_prompt.rstrip() + "\n\n将交付文件写入 outputs/，不要修改 inputs/。\n"
    plan["prompt_adapter_appendix"] = "将交付文件写入 outputs/，不要修改 inputs/。"
    plan["source_prompt_sha256"] = hashlib.sha256(original_prompt.encode()).hexdigest()
    write_json(evidence / "plan.json", plan)
    (evidence / "submitted-prompt.txt").write_text(prompt, encoding="utf-8")
    started = time.monotonic()
    started_at = stamp()
    proc = subprocess.Popen(args, cwd=workspace, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW,
                            env=os.environ.copy())
    write_json(evidence / "launch.json", {"pid": proc.pid, "started_at": started_at,
                                         "session_id": session_id, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    threads = []
    for stream, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr)):
        thread = threading.Thread(target=capture, args=(pipe, evidence / f"{stream}.raw",
                                  evidence / f"{stream}-receipts.jsonl", stream, started), daemon=True)
        thread.start()
        threads.append(thread)
    proc.stdin.write(prompt.encode("utf-8"))
    proc.stdin.close()
    timed_out = False
    try:
        proc.wait(timeout=max(0.1, opts.timeout - (time.monotonic() - started)))
    except subprocess.TimeoutExpired:
        timed_out = True
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True,
                       timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        proc.wait(timeout=30)
    for thread in threads:
        thread.join(timeout=10)
    finished_at = stamp()
    collected = []
    collection = evidence / "collected"
    collection.mkdir()
    for name in case["required_outputs"]:
        candidates = [workspace / "outputs" / name, workspace / name]
        source = next((p for p in candidates if p.is_file()), None)
        if source and source.resolve().is_relative_to(workspace.resolve()):
            dest = collection / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            collected.append({"name": name, "source_relative_path": source.relative_to(workspace).as_posix(),
                              "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
    final_inventory = inventory(workspace)
    unchanged = all(final_inventory.get(name) == digest for name, digest in initial.items())
    observed = extract_observations(evidence / "stdout.raw")
    write_json(evidence / "observations.private.json", observed)
    result = {"run_id": run_id, "formal_sample": False, "started_at": started_at,
              "finished_at": finished_at, "elapsed_seconds": time.monotonic() - started,
              "exit_code": proc.returncode, "timed_out": timed_out,
              "inputs_and_prompt_unchanged": unchanged, "collected": collected,
              "required_outputs_present": len(collected) == len(case["required_outputs"]),
              "final_inventory": final_inventory}
    write_json(evidence / "result.json", result)
    import sys
    sys.path.insert(0, str(ROOT))
    from harness_eval.core import evaluate
    objective = evaluate(case_dir, collection)
    write_json(evidence / "objective.private.json", objective)
    write_json(evidence / "evidence-inventory.json", inventory(evidence))
    print(json.dumps({"run_id": run_id, "exit_code": proc.returncode, "timed_out": timed_out,
                      "elapsed_seconds": round(result["elapsed_seconds"], 2),
                      "outputs_present": result["required_outputs_present"],
                      "evidence": str(evidence)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
