"""Prepare/export reviewed native Yuanbao/Doubao pilots; never controls the UI.

Prepare copies canonical bytes only. Export consumes actual observations and
native download receipts; it does not generate or repair participant outputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

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


def locations(product, case):
    name = f"{product}-{case}-desktop-r1"
    return name, Path("D:/harness-participants") / ("pilot-" + name), ROOT / "private/pilots" / name, ROOT / "public/pilots" / name


def prepare(product, case):
    name, workspace, private, _ = locations(product, case)
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
        "case_id": case, "prepared_at": now(), "workspace": str(workspace),
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
        "note": "Preparation is not product evidence. Native UI mode/version, accepted uploads and native downloads must be recorded later.",
    })
    print(json.dumps({"prepared": name, "workspace": str(workspace), "private": str(private),
                      "submitted_prompt": str(private / "submitted-prompt.txt"),
                      "initial_files": list(initial), "outputs_initially_empty": True,
                      "submitted": False}, ensure_ascii=False))


def export(product, case):
    raise NotImplementedError("Export requires reviewed actual native observations and download receipts; preparation alone is never exportable")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "export"))
    parser.add_argument("--product", required=True, choices=("yuanbao", "doubao"))
    parser.add_argument("--case", required=True, choices=CASE_IDS)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.product, args.case)
    else:
        export(args.product, args.case)
