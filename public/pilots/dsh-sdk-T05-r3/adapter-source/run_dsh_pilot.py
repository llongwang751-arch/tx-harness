"""Run a real DeepSeek Harness headless pilot; default is a dry run.

Credentials stay in the product's own store. Raw logs, including any reasoning,
are private. This adapter does not change, repair, or grade product outputs.
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


ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inventory(folder):
    return {p.relative_to(folder).as_posix(): digest(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--case", default="T01", choices=["T01", "T02", "T03", "T05"])
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--participant-root", type=Path, default=Path("D:/harness-participants"))
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args()
    if args.replicate < 1 or not 1 <= args.timeout_seconds <= 1200:
        parser.error("replicate must be positive; timeout must be between 1 and 1200 seconds")
    participant_root = args.participant_root.resolve()
    if participant_root == ROOT or participant_root.is_relative_to(ROOT):
        parser.error("the participant directory must be outside the evaluator repository")
    case_dir = ROOT / "cases" / args.case
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    workspace = participant_root / f"pilot-dsh-{args.case}-r{args.replicate}"
    private = ROOT / "private" / "pilots" / f"dsh-{args.case}-r{args.replicate}"
    install = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "DeepSeek Harness"
    executable = install / "DeepSeek Harness.exe"
    cli = install / "resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js"
    bundled_skills = install / "resources/runtime/office-skills"
    patch = private / "dsh-model.patch.yml"
    command = [str(executable), "--expose-internals", str(cli), "--patch", str(patch),
               "--profile", "headless", "--json", "-"]
    payload = {"product": "dsh", "surface": "desktop-bundled CLI", "profile": "headless",
               "track": "pilot", "case": args.case, "replicate": args.replicate,
               "workspace": str(workspace), "private_logs": str(private),
               "requested_provider": "deepseek-account", "requested_model": "deepseek-flash",
               "requested_reasoning_effort": "high", "timeout_seconds": args.timeout_seconds,
               "command": command, "execute": args.execute}
    if not args.execute:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if workspace.exists() or private.exists():
        raise SystemExit("Refusing to overwrite an existing participant or evidence directory")
    if not executable.is_file() or not bundled_skills.is_dir():
        raise SystemExit("Required installed product files were not found")
    workspace.mkdir(parents=True)
    private.mkdir(parents=True)
    shutil.copytree(case_dir / case["input_dir"], workspace / "inputs")
    (workspace / "outputs").mkdir()
    original_prompt = (case_dir / case["prompt_file"]).read_text(encoding="utf-8")
    prompt = original_prompt + "\n\n交付位置约定：将上述交付文件写入 outputs/；不要修改 inputs/。\n"
    (workspace / "prompt.md").write_text(prompt, encoding="utf-8")
    (private / "submitted-prompt.md").write_text(prompt, encoding="utf-8")
    # This is a one-run overlay. It excludes user/project skills while retaining
    # the installed product's Office skills, and removes task network tools.
    skills_yaml = json.dumps(str(bundled_skills).replace("\\", "/"), ensure_ascii=False)
    patch.write_text(
        "- id: agent-default-model\n  config:\n    provider: deepseek-account\n"
        "    model: deepseek-flash\n    reasoningEffort: high\n"
        "- id: skill-filesystem\n  config:\n    includeDefaultRoots: false\n"
        f"    bundledSkillDir: {skills_yaml}\n    watch: false\n"
        "- id: tool-web\n  disabled: true\n", encoding="utf-8")
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    env["DSH_PERMISSION_MODE"] = "workspace-write"
    payload["initial_files"] = inventory(workspace)
    payload["patch_sha256"] = digest(patch)
    payload["runner_sha256"] = digest(Path(__file__))
    payload["installation_version"] = "0.2.0-rc.2"
    payload["limitations"] = [
        "CLI/headless is not the desktop UI surface.",
        "Workspace-write does not prove confinement of reads, network, or processes.",
        "Default DSH home/profile preferences other than the explicit overlay may remain active.",
        "Machine-readable events may be truncated; raw reasoning remains private.",
        "Account route and advisory model selection are recorded; server-side model identity is not proven.",
    ]
    payload["started_at"] = now()
    write_json(private / "run.json", payload)
    started = time.monotonic()
    lock = threading.Lock()
    with (private / "received.jsonl").open("w", encoding="utf-8") as received:
        def collect(pipe, name):
            with (private / f"{name}.raw").open("wb") as raw:
                for line in iter(pipe.readline, b""):
                    raw.write(line)
                    raw.flush()
                    item = {"received_at": now(), "stream": name,
                            "line": line.decode("utf-8", errors="replace").rstrip("\r\n")}
                    with lock:
                        received.write(json.dumps(item, ensure_ascii=False) + "\n")
                        received.flush()
        try:
            process = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            payload["pid"] = process.pid
            write_json(private / "run.json", payload)
            threads = [threading.Thread(target=collect, args=(process.stdout, "stdout")),
                       threading.Thread(target=collect, args=(process.stderr, "stderr"))]
            for thread in threads:
                thread.start()
            process.stdin.write(prompt.encode("utf-8"))
            process.stdin.close()
            try:
                process.wait(timeout=args.timeout_seconds)
                payload["timed_out"] = False
            except subprocess.TimeoutExpired:
                payload["timed_out"] = True
                # Terminate the precisely identified child tree; never stop the
                # user's desktop product or another participant's process.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=30)
            for thread in threads:
                thread.join(timeout=30)
            payload["exit_code"] = process.returncode
        except Exception as error:
            payload["runner_error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            payload["finished_at"] = now()
            payload["elapsed_seconds"] = round(time.monotonic() - started, 3)
            payload["final_files"] = inventory(workspace)
            payload["outputs"] = inventory(workspace / "outputs")
            write_json(private / "run.json", payload)
    # Print only non-sensitive lifecycle facts, never raw product logs.
    print(json.dumps({key: payload.get(key) for key in
                      ("product", "case", "workspace", "private_logs", "exit_code",
                       "timed_out", "elapsed_seconds", "outputs")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
