"""Run a preregistered file delivery check in one native CLI."""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness_eval.core import read_json, sha256, write_json
from scripts.run_codex_pilot import command, native_codex, now, run_stage, safe_env, stop_tree
from run_dsh_sdk_pilot import SdkPeer

BASE = ROOT / "supplements/five-surface-v1"
PIN = "7876f914bdbee57c6b19a1d1bfa53f1190bdd77d"
WORK = ROOT.parent / "tx-harness-participants/five-surface-20261119"
PRIVATE = ROOT / "private/five-surface-20261119"


def dsh(workspace, evidence, prompt, receipt):
    install = Path(os.environ["LOCALAPPDATA"]) / "Programs/DeepSeek Harness"
    executable = install / "DeepSeek Harness.exe"
    archive = install / "resources/app.asar"
    if not archive.is_file():
        raise ValueError("The installed Electron package is missing.")
    cli = archive / "dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js"
    patch = evidence / "profile.json"
    write_json(patch, [{"id": "skill-filesystem", "config": {
        "includeDefaultRoots": False, "watch": False,
        "bundledSkillDir": (install / "resources/runtime/office-skills").as_posix()}},
        {"id": "tool-web", "disabled": True}])
    env = {**safe_env(), "ELECTRON_RUN_AS_NODE": "1", "DSH_PERMISSION_MODE": "workspace-write"}
    proc = subprocess.Popen([str(executable), "--expose-internals", str(cli),
                             "--patch", str(patch), "--profile", "sdk"], env=env, cwd=workspace,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    peer = SdkPeer(proc, evidence, "transfer-" + uuid.uuid4().hex)
    deadline = time.monotonic() + 180
    try:
        n, _ = peer.send("initialize", {"cwd": str(workspace), "provider": "deepseek-account",
                                       "model": "deepseek-flash", "reasoningEffort": "high"})
        peer.response(n, deadline)
        n, at = peer.send("session/prompt", {"sessionId": peer.session_id,
                                          "contentBlocks": [{"type": "text", "text": prompt}]})
        receipt["submitted_at"] = at
        peer.response(n, deadline)
        receipt["accepted"] = True
        while time.monotonic() < deadline:
            peer.consume()
            if peer.status == "idle" and peer.ends:
                receipt["completed"] = True
                break
            if proc.poll() is not None:
                break
        n, _ = peer.send("shutdown")
        peer.response(n, time.monotonic() + 10)
        proc.stdin.close()
        receipt["exit_code"] = proc.wait(timeout=10)
        receipt["model"] = "deepseek-flash"
        if peer.texts:
            receipt["final_reply"] = list(peer.texts.values())[-1]["event"]["text"]
    finally:
        stop_tree(proc)
        peer.close_logs()


def codex(workspace, evidence, prompt, receipt):
    executable = native_codex()
    receipt["cli_version"] = subprocess.check_output([str(executable), "--version"], env=safe_env()).decode().strip()
    receipt["model"] = "clean CLI service default"
    started = time.monotonic()
    result = run_stage(command(executable, workspace, None), prompt, workspace, evidence, "initial",
                       started, started + 180)
    receipt.update(submitted_at=result["submitted_at"], accepted=bool(result["session_id"]),
                   exit_code=result["exit_code"], completed=False)
    for line in (evidence / "initial.stdout.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("type") == "turn.completed":
            receipt["completed"] = True
        elif row.get("type") == "item.completed" and row.get("item", {}).get("type") == "agent_message":
            receipt["final_reply"] = row["item"]["text"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", choices=["dsh", "codex"])
    product = parser.parse_args().product
    run_id = read_json(BASE / "protocol.json")["run_ids"][product]
    for source in ["input.csv", "prompt.txt", "protocol.json"]:
        frozen = subprocess.check_output(["git", "show", f"{PIN}:supplements/five-surface-v1/{source}"], cwd=ROOT)
        if (BASE / source).read_bytes() != frozen:
            raise ValueError("Frozen exercise differs from its prior Git bytes.")
    workspace, evidence = WORK / run_id, PRIVATE / run_id
    if list(workspace.iterdir()) != [workspace / "input.csv"] or sha256(workspace / "input.csv") != sha256(BASE / "input.csv"):
        raise ValueError("Workspace must contain just the verified staged input.")
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = {"run_id": run_id, "product": product, "accepted": False, "completed": False,
               "started_at": now(), "input_sha256": sha256(workspace / "input.csv")}
    try:
        (dsh if product == "dsh" else codex)(workspace, evidence, (BASE / "prompt.txt").read_text(encoding="utf-8"), receipt)
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        receipt["ended_at"] = now()
        receipt["artifact_observed"] = (workspace / "receipt.json").is_file()
        write_json(evidence / "operator.json", receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != "final_reply"}, ensure_ascii=False))
    return 0 if receipt["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
