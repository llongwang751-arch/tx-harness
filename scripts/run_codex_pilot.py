"""Run an independent, bounded Codex CLI task; default is a no-write pilot plan.

This is an adapter for a controlled CLI entrypoint, not the Codex desktop surface and
not a model/Skill/Harness causal comparison. It never uses the evaluator's agent
as the tested product. Only --execute starts a real native Codex process.

The native CLI reuses its existing login without reading or copying credentials.
Logs remain private and require review before publication. T04 uses the exact
thread ID emitted by the initial process, never --last. When the 120-second
release occurs during a running turn, the adapter interrupts that turn before
resuming; the interruption and actual message delivery times are recorded.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from harness_eval.__main__ import (append_event, command_finalize, command_prepare,
                                  command_release)
from harness_eval.core import inventory, read_json, sha256, write_json

CASES = ("T01", "T02", "T03", "T04", "T05")
DELIVERY_SUFFIX = "将交付文件写入 outputs/，不要修改 inputs/。"
ENV_NAMES = {"PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT",
             "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "USERNAME",
             "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "CODEX_HOME",
             "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def native_codex(requested=None):
    """Use the actual native binary; resolve the official npm shim if needed."""
    if requested:
        supplied = Path(requested).expanduser().resolve()
        if supplied.suffix.lower() == ".exe" and supplied.is_file():
            return supplied
        bases = [supplied.parent]
    else:
        found = shutil.which("codex.exe")
        if found:
            return Path(found).resolve()
        bases = [Path(os.environ.get("APPDATA", "")) / "npm"]
    matches = []
    for base in bases:
        package = base / "node_modules/@openai/codex"
        matches.extend(package.glob("node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"))
        matches.extend(package.glob("vendor/*/bin/codex.exe"))
    matches = sorted(set(p.resolve() for p in matches if p.is_file()))
    if len(matches) != 1:
        raise ValueError("Cannot identify one native Codex binary; pass --codex <codex.exe>.")
    return matches[0]


def safe_env():
    # Do not forward API keys or arbitrary secret variables to the tested CLI.
    # Keep saved-login location and transport proxies without printing values.
    return {k: v for k, v in os.environ.items() if k.upper() in ENV_NAMES}


def toml(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return "{" + ",".join(f"{toml(k)}={toml(v)}" for k, v in value.items()) + "}"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def command(executable, workspace, model, *, session_id=None, persist_session=False):
    fs = {":root": "deny", ":minimal": "read", str(ROOT): "deny",
          str(workspace): "write", str(workspace / "inputs"): "read",
          str(workspace / "prompt.md"): "read"}
    # --ignore-user-config also omits the desktop's Windows sandbox preference.
    # Select the supported native sandbox explicitly and allow only installed
    # official runtime directories needed to launch file tools, not user data.
    runtime_dirs = [Path(os.environ.get("USERPROFILE", "")) / ".cache/codex-runtimes/codex-primary-runtime/dependencies",
                    executable.parent]
    for directory in runtime_dirs:
        if directory.is_dir():
            fs[str(directory.resolve())] = "read"
    config = {
        "default_permissions": "harness_pilot",
        "permissions.harness_pilot.extends": ":workspace",
        "permissions.harness_pilot.filesystem": fs,
        "permissions.harness_pilot.network.enabled": False,
        "approval_policy": "never",
        "web_search": "disabled",
        "project_doc_max_bytes": 0,
        "features.skip_host_skill_discovery": True,
        "features.prefer_mxc": True,
        "features.plugins": False,
        "features.hooks": False,
        "features.memories": False,
        "features.computer_use": False,
        "features.in_app_browser": False,
        "features.browser_use": False,
        "features.browser_use_external": False,
        "features.apps": False,
        "shell_environment_policy.inherit": "none",
        "shell_environment_policy.set": {
            k: v for k, v in safe_env().items()
            if k.upper() not in {"CODEX_HOME", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
        },
    }
    args = [str(executable), "--no-daemon", "--strict-config", "--cd", str(workspace), "exec"]
    if session_id:
        args += ["resume"]
    args += ["--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--json"]
    for key, value in config.items():
        args += ["-c", key + "=" + toml(value)]
    if model:
        args += ["--model", model]
    # The initial T04 session must persist so exec resume can continue it.
    # Other pilots are fresh and ephemeral, without reusable task history.
    if not session_id and not persist_session:
        args += ["--ephemeral"]
    if session_id:
        args += [session_id]
    args += ["-"]  # exact prompt via stdin, never a shell command interpolation
    return args


def public_command(args):
    """Keep the launch receipt useful without dumping environment values."""
    return [part.split("=", 1)[0] + "=<environment values omitted>"
            if part.startswith("shell_environment_policy.set=") else part for part in args]


def request_candidate(event):
    if event.get("type") != "item.completed":
        return None
    item = event.get("item", {})
    if item.get("type") != "agent_message":
        return None
    value = item.get("text", "")
    # Deliberately narrow: a future/hypothetical plan is not an input request.
    # When meaning is uncertain, do not actively release; the 120-second
    # passive release remains available and the full message is retained.
    uncertain = re.search(r"若|如果|可能|会请求|请求补充|将请求|会请|将请|如缺|如未|"
                          r"推荐|示例|例如|\b(?:if|would|will request|will ask)\b", value, re.I)
    if uncertain:
        return None
    asks = re.search(r"(?:^|[。！？!?；;：:\n])\s*(?:[-*>]\s*)?"
                     r"(?:请(?:提供|补充|上传)\s*[`\"“]?\s*(?:rates\.json|汇率(?:文件|表|数据)?)|"
                     r"please\s+(?:provide|supply|upload)\s+(?:the\s+)?[`\"]?rates\.json)", value, re.I)
    return value if asks else None


def stop_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        # PID belongs to this Popen; no filesystem deletion or broad process match.
        subprocess.run(["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    else:
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        proc.wait(timeout=5)


def run_stage(args, prompt, workspace, evidence, stage, started, deadline,
              release_callback=None, release_not_before_epoch=None):
    """Capture original bytes plus timestamped native events, with a watchdog."""
    messages = queue.Queue()
    stem = evidence / stage
    captured = []
    session_id = None
    interrupted = False
    timed_out = False
    release = None
    proc = subprocess.Popen(args, cwd=workspace, env=safe_env(), stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0,
                            start_new_session=os.name != "nt")

    def drain(stream, name):
        with (stem.with_suffix("." + name)).open("wb") as target:
            for line in iter(stream.readline, b""):
                target.write(line)
                target.flush()
                if name == "stdout.jsonl":
                    messages.put((now(), time.monotonic(), line.decode("utf-8", errors="replace")))
        stream.close()

    readers = [threading.Thread(target=drain, args=(proc.stdout, "stdout.jsonl"), daemon=True),
               threading.Thread(target=drain, args=(proc.stderr, "stderr.txt"), daemon=True)]
    for reader in readers:
        reader.start()
    submitted_at = now()
    proc.stdin.write(prompt.encode("utf-8"))
    proc.stdin.close()
    try:
        while True:
            while not messages.empty():
                at, monotonic_at, line = messages.get_nowait()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    event = {"type": "non_json_stdout", "raw": line}
                observed = {"at": at, "elapsed_seconds": monotonic_at - started, "event": event}
                captured.append(observed)
                if event.get("type") == "thread.started":
                    session_id = event.get("thread_id")
                candidate = request_candidate(event)
                if release_callback and release is None and candidate and monotonic_at - started <= 120:
                    release = release_callback("active", observed)
            elapsed = time.monotonic() - started
            # Compare against the recorded start timestamp as well as monotonic
            # time: the latter is initialized a moment before the start event.
            # This avoids a passive release receipt at e.g. 119.999 seconds.
            if (release_callback and release is None and elapsed >= 120
                    and (release_not_before_epoch is None or time.time() >= release_not_before_epoch)):
                release = release_callback("passive", None)
            if time.monotonic() >= deadline and proc.poll() is None:
                timed_out = True
                stop_tree(proc)
            # codex exec consumes one input turn. After file release, move to the
            # exact saved thread with the uniform supplement message. Record any
            # running-turn interruption as an adapter action, never hide it.
            if release is not None and proc.poll() is None:
                interrupted = True
                stop_tree(proc)
            if proc.poll() is not None and all(not reader.is_alive() for reader in readers) and messages.empty():
                # For T04 with a finished initial turn but no request, still wait
                # to the preregistered 120-second passive release, within budget.
                if not release_callback or release is not None or time.monotonic() >= deadline:
                    break
            time.sleep(0.05)
    finally:
        stop_tree(proc)
        for reader in readers:
            reader.join(timeout=5)
    result = {"stage": stage, "session_id": session_id, "exit_code": proc.returncode,
              "submitted_at": submitted_at, "ended_at": now(), "timed_out": timed_out,
              "interrupted_for_scheduled_resume": interrupted,
              "release": release, "native_event_count": len(captured)}
    write_json(stem.with_suffix(".observed.json"), captured)
    write_json(stem.with_suffix(".result.json"), result)
    return result


def copy_outputs(case, workspace, target, deadline_epoch):
    """Collect original deliverables, whether CLI put them in outputs or cwd."""
    collected, conflicts, late = [], [], []
    for name in case["required_outputs"]:
        primary, alternate = workspace / "outputs" / name, workspace / name
        for source in (primary, alternate):
            parents = [source, *source.parents]
            local = [p for p in parents if p == workspace or p.is_relative_to(workspace)]
            if not source.resolve().is_relative_to(workspace.resolve()) or any(
                p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in local
            ):
                raise ValueError("Participant output cannot be a link: " + name)
        if primary.is_file() and alternate.is_file() and sha256(primary) != sha256(alternate):
            conflicts.append(name)
            continue
        source = primary if primary.is_file() else alternate
        if source.is_file():
            if source.stat().st_mtime > deadline_epoch:
                late.append(name)
                continue
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            collected.append({"path": name, "source_relative_path": source.relative_to(workspace).as_posix(),
                              "sha256": sha256(destination)})
    return {"collected": collected, "conflicting_duplicate_deliverables": conflicts,
            "outputs_modified_after_deadline_excluded": late}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--replicate", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--track", choices=("pilot", "product_default"), default="pilot",
                        help="Formal product_default requires a preregistered protocol before execution")
    parser.add_argument("--attempt", type=int, choices=range(1, 100), default=1,
                        help="Pilot infrastructure attempt; all earlier attempts remain preserved")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "private/codex-pilot")
    parser.add_argument("--participant-root", type=Path, default=ROOT.parent / "tx-harness-participants")
    parser.add_argument("--codex", help="Native codex.exe or its official npm codex.ps1 shim")
    parser.add_argument("--model", help="Optional preselected model; omitted uses this clean CLI's default")
    parser.add_argument("--operator", default="automated_native_cli_adapter")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Explicitly start a real product run")
    mode.add_argument("--dry-run", action="store_true", help="Default: show the plan without writing files")
    options = parser.parse_args(argv)
    executable = native_codex(options.codex)
    # Attempt number belongs to the storage path, not the evaluator's closed
    # track vocabulary. The early attempt02 naming error is preserved in its
    # original private package; this fixes future collections without rerunning.
    track = options.track
    run_id = f"{track}-codex-{options.case}-r{options.replicate}"
    protocol = read_json(ROOT / "config/protocol.json")
    attempt_parent = Path() if options.attempt == 1 else Path(f"attempt{options.attempt:02d}")
    runs_dir = options.runs_dir.resolve() / attempt_parent
    run = runs_dir / run_id
    workspace = options.participant_root.resolve() / attempt_parent / run_id
    if workspace.is_relative_to(ROOT) or ROOT.is_relative_to(workspace):
        raise ValueError("Participant root must be outside and must not contain the evaluation repository.")
    args = command(executable, workspace, options.model, persist_session=options.case == "T04")
    plan = {"execute": options.execute, "run": str(run), "participant_workspace": str(workspace),
            "case": options.case, "attempt": options.attempt,
            "surface": "controlled native Codex CLI", "track": track,
            "protocol_status": protocol["status"], "budget_seconds": 1200,
            "command": public_command(args), "prompt": "exact case prompt plus uniform delivery suffix through stdin",
            "initial_files": ["prompt.md", "inputs/**", "empty outputs/"],
            "delivery_adapter_suffix": DELIVERY_SUFFIX,
            "t04": "observe native agent request; release <=120s actively, otherwise at120s; resume exact thread",
            "limitations": ["CLI results do not stand in for Codex desktop results",
                            "restricted permissions are configured; enforcement requires pilot verification",
                            "T04 request pattern is a candidate for human semantic review",
                            "A running initial T04 turn is interrupted for scheduled resume and disclosed",
                            "No score, manual review, seal, redaction approval, or publication is automatic"],
            "official_sources": ["https://learn.chatgpt.com/docs/non-interactive-mode",
                                 "https://learn.chatgpt.com/docs/permissions",
                                 "https://learn.chatgpt.com/docs/developer-commands?surface=cli"]}
    if not options.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if track == "product_default" and protocol["status"] != "preregistered":
        raise ValueError("Formal execution requires protocol.status=preregistered; no run was created.")
    if run.exists() or workspace.exists():
        raise ValueError("Run or participant workspace already exists; cannot overwrite or rerun selectively.")
    version = subprocess.run([str(executable), "--version"], capture_output=True, text=True,
                             encoding="utf-8", env=safe_env(), timeout=30, check=True).stdout.strip()
    status = subprocess.run([str(executable), "login", "status"], capture_output=True,
                            env=safe_env(), timeout=30)
    if status.returncode != 0:
        raise ValueError("Existing Codex CLI login is not ready. No authentication files were read.")
    command_prepare(argparse.Namespace(product="codex", case=options.case, replicate=options.replicate,
                                       track=track, runs_dir=runs_dir))
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run / "workspace", workspace)
    case = read_json(ROOT / "cases" / options.case / "case.json")
    evidence = run / "evidence"
    initial_hashes = inventory(workspace)
    shutil.copyfile(Path(__file__), evidence / "runner-source.py")
    original_prompt = (workspace / "prompt.md").read_text(encoding="utf-8")
    submitted_prompt = original_prompt.rstrip() + "\n\n" + DELIVERY_SUFFIX + "\n"
    (evidence / "submitted-prompt.md").write_text(submitted_prompt, encoding="utf-8", newline="\n")
    meta = read_json(run / "meta.json")
    meta.update(operator=options.operator, surface="Codex CLI", product_version=version,
                model=options.model or "not_disclosed_clean_cli_default", model_visibility="explicit_cli_flag" if options.model else "unknown",
                mode="exec; no daemon; controlled permissions; prefer MXC", account_tier="not_disclosed",
                region="not_disclosed", memory_condition="fresh exec; memories disabled",
                skill_condition="host_skill_discovery_skipped; plugins disabled; built-in state not independently verified",
                permissions="named profile: root deny/minimal read/workspace write/inputs read/network false; approval never",
                environment={"os": sys.platform, "python": sys.version.split()[0], "binary_sha256": sha256(executable)},
                recording_limitations="native JSONL and stderr; no GUI; hidden service state not observed; no causal isolation")
    write_json(run / "meta.json", meta)
    started = time.monotonic()
    deadline = started + 1200
    deadline_epoch = time.time() + 1200
    start_at = now()
    write_json(evidence / "launch.json", {**plan, "version": version, "auth_ready": True,
                                         "started_at": start_at, "initial_hashes": initial_hashes,
                                         "original_prompt_sha256": sha256(workspace / "prompt.md"),
                                         "submitted_prompt_sha256": sha256(evidence / "submitted-prompt.md"),
                                         "runner_source_sha256": sha256(evidence / "runner-source.py")})
    append_event(run, "start", "Adapter starts a fresh native CLI exec with the exact task prompt plus the uniform output-directory convention; no evaluator files supplied.",
                 ["evidence/launch.json", "evidence/submitted-prompt.md"], start_at)

    def release_file(kind, observed):
        event_id = None
        if observed:
            write_json(evidence / "missing-input-request.json", observed)
            event_id = append_event(run, "observation", "Native agent message requests missing exchange rates; automated candidate requires semantic review.",
                                    ["evidence/missing-input-request.json"], observed["at"])["id"]
        command_release(argparse.Namespace(run=run, file="rates.json", mode=kind,
                                           request_event=event_id, at=now(),
                                           note="Automated native CLI protocol release; message delivery follows in exact-session resume."))
        shutil.copyfile(run / "workspace/inputs/rates.json", workspace / "inputs/rates.json")
        return {"mode": kind, "file_available_at": now(), "request_event": event_id,
                "file_sha256": sha256(workspace / "inputs/rates.json")}

    results = []
    first = run_stage(args, submitted_prompt, workspace,
                      evidence, "initial", started, deadline,
                      release_callback=release_file if options.case == "T04" else None,
                      release_not_before_epoch=datetime.fromisoformat(start_at).timestamp() + 120)
    results.append(first)
    append_event(run, "tool_result", "Initial native CLI turn captured; see original JSONL and stderr, including disclosed adapter interruption.",
                 ["evidence/initial.stdout.jsonl", "evidence/initial.stderr.txt", "evidence/initial.result.json"], now())
    if options.case == "T04" and first["session_id"] and first["release"] and time.monotonic() < deadline:
        supplement = case["release_protocol"]["response_text"]
        resume_args = command(executable, workspace, options.model, session_id=first["session_id"])
        write_json(evidence / "resume-input.json", {"session_id": first["session_id"], "input": supplement,
                                                    "submitted_at": now(), "command": public_command(resume_args)})
        append_event(run, "observation", "Submit uniform rates supplement to the exact initial native thread ID; no new-task or --last substitution.",
                     ["evidence/resume-input.json"], now())
        resumed = run_stage(resume_args, supplement, workspace, evidence, "resume", started, deadline)
        results.append(resumed)
        append_event(run, "tool_result", "Exact-thread resumed native turn captured.",
                     ["evidence/resume.stdout.jsonl", "evidence/resume.stderr.txt", "evidence/resume.result.json"], now())
    collected = copy_outputs(case, workspace, run / "workspace/outputs", deadline_epoch)
    original_unchanged = all((workspace / name).is_file() and sha256(workspace / name) == digest
                             for name, digest in initial_hashes.items())
    write_json(evidence / "collection.json", {**collected, "initial_inputs_unchanged": original_unchanged,
                                               "participant_final_inventory": inventory(workspace)})
    timed_out = any(result["timed_out"] for result in results) or time.monotonic() > deadline
    delivered = len(collected["collected"]) == len(case["required_outputs"])
    status_name = "timeout" if timed_out else "completed" if delivered and original_unchanged and results[-1]["exit_code"] == 0 else "failed"
    finish = append_event(run, "finish", f"Native CLI {track} run ended: {status_name}; required-file presence does not assert correctness.",
                          ["evidence/collection.json"], now())
    command_finalize(argparse.Namespace(run=run, status=status_name, at=finish["at"],
                                        note="Native CLI execution and unmodified deliverables captured; awaiting correctness, semantic, privacy and manual review."))
    print(json.dumps({"run": str(run), "status": status_name, "files_collected": len(collected["collected"]),
                      "review_required": True, "sealed": False}, ensure_ascii=False))
    return 0 if status_name == "completed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("Runner error: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
