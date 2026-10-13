"""Prepare byte-preserving, answer-free web attachments; never submit a task.

The destination must be outside this repository. Operator manifests and T04's
held release are separate from initial attachments. No browser or API is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
CASE_IDS = ("T01", "T02", "T03", "T04", "T05")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def case_files(case: str) -> list[Path]:
    source = ROOT / "cases" / case
    inputs = source / "inputs"
    paths = [source / "prompt.md"] + sorted(p for p in inputs.rglob("*") if p.is_file())
    for path in paths:
        allowed = path == source / "prompt.md" or within(path.resolve(), inputs.resolve())
        if path.is_symlink() or not allowed or not within(path.resolve(), source.resolve()):
            raise ValueError(f"Input path escapes the allowlist: {path.name}")
    return paths


def prepare_case(case: str, destination: Path, make_zip: bool) -> dict:
    source = ROOT / "cases" / case
    target = destination / case
    target.mkdir()
    files = case_files(case)
    spec = json.loads((source / "case.json").read_bytes())
    initial = []
    mapping = []
    input_paths = [p for p in files if p != source / "prompt.md"]
    names = [p.name for p in input_paths]
    if len(names) != len(set(names)):
        raise ValueError(f"{case}: flat attachment names collide; no automatic rename")
    for path in files:
        relative = path.relative_to(source).as_posix()
        data = path.read_bytes()
        copy = target / "initial" / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(data)
        initial.append({"logical_path": relative, "bytes": len(data), "sha256": sha(data)})
        if relative.startswith("inputs/"):
            mapping.append({"logical_path": relative, "attachment_name": path.name,
                            "upload_verified": False, "server_path": None})
    release = None
    if case == "T04":
        release_spec = spec["release_protocol"]
        assert release_spec["initial_delivery"] == ["prompt.md", "inputs/trades.csv"]
        assert [p.relative_to(source).as_posix() for p in files] == release_spec["initial_delivery"]
        release_source = source / "releases" / "rates.json"
        data = release_source.read_bytes()
        held = target / "held-release" / "rates.json"
        held.parent.mkdir()
        held.write_bytes(data)
        release = {"not_initially_uploadable": True, "relative_file": "held-release/rates.json",
                   "logical_target": "inputs/rates.json", "attachment_name": "rates.json",
                   "bytes": len(data), "sha256": sha(data),
                   "response_text": release_spec["response_text"],
                   "release_protocol": release_spec, "released": False,
                   "actual_request_at": None, "actual_upload_available_at": None,
                   "actual_supplement_sent_at": None}
        (target / "held-release" / "supplement-message.txt").write_bytes(
            release_spec["response_text"].encode("utf-8"))
    zip_record = None
    if make_zip:
        zip_path = target / "initial-inputs.zip"
        with ZipFile(zip_path, "w", compression=ZIP_STORED) as bundle:
            for path in input_paths:
                info = ZipInfo(path.relative_to(source).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, path.read_bytes())
        zip_record = {"path": zip_path.name, "sha256": sha(zip_path.read_bytes()),
                      "entries": [p.relative_to(source).as_posix() for p in input_paths],
                      "supported_by_target_mode": "unknown",
                      "default_upload": False}
    write_json(target / "attachment-path-map.json", {
        "operator_only": True, "status": "planned_not_observed",
        "rule": "Keep original file bytes and basenames; map flat names to logical paths outside task text.",
        "initial_attachments": mapping,
    })
    manifest = {
        "schema": "web-upload-preparation-v1", "case_id": case,
        "operator_only": True, "not_product_evidence": True,
        "product_submission_performed": False, "formal_eligible": False,
        "initial_files": initial, "required_output_paths": spec["required_outputs"],
        "source_case_spec_sha256": sha((source / "case.json").read_bytes()),
        "source_protocol_sha256": sha((ROOT / "config/protocol.json").read_bytes()),
        "prompt_policy": "Paste canonical prompt.md unchanged; separately record observed submit and actual transport visibility.",
        "attachment_path_map": "attachment-path-map.json",
        "optional_input_zip": zip_record, "held_release": release,
        "excluded_from_product": ["oracle.json", "expected/", "case.json", "checks", "evaluation code",
                                  "previous outputs", "operator manifests", "held-release before protocol trigger"],
    }
    write_json(target / "preparation.json", manifest)
    return {"case_id": case, "input_count": len(input_paths),
            "input_bytes": sum(p.stat().st_size for p in input_paths),
            "source_prompt_sha256": sha((source / "prompt.md").read_bytes()),
            "release_initially_absent": case == "T04"}


def verify_case(case: str, destination: Path) -> dict:
    source = ROOT / "cases" / case
    target = destination / case
    manifest = json.loads((target / "preparation.json").read_bytes())
    expected = {p.relative_to(source).as_posix(): p for p in case_files(case)}
    actual = {p.relative_to(target / "initial").as_posix(): p
              for p in (target / "initial").rglob("*") if p.is_file()}
    if set(actual) != set(expected):
        raise ValueError(f"{case}: unexpected or missing initial file")
    recorded = {row["logical_path"]: row for row in manifest["initial_files"]}
    if set(recorded) != set(expected):
        raise ValueError(f"{case}: manifest initial file set differs")
    for relative, original in expected.items():
        data = actual[relative].read_bytes()
        if data != original.read_bytes() or sha(data) != recorded[relative]["sha256"] or len(data) != recorded[relative]["bytes"]:
            raise ValueError(f"{case}: source byte/hash mismatch: {relative}")
    if manifest["source_case_spec_sha256"] != sha((source / "case.json").read_bytes()) or manifest["source_protocol_sha256"] != sha((ROOT / "config/protocol.json").read_bytes()):
        raise ValueError(f"{case}: source specification changed after preparation")
    mapping = json.loads((target / "attachment-path-map.json").read_bytes())
    expected_mapping = [{"logical_path": r, "attachment_name": p.name,
                         "upload_verified": False, "server_path": None}
                        for r, p in expected.items() if r.startswith("inputs/")]
    if mapping["initial_attachments"] != expected_mapping:
        raise ValueError(f"{case}: planned attachment map changed")
    bundle = manifest["optional_input_zip"]
    if bundle:
        path = target / bundle["path"]
        if sha(path.read_bytes()) != bundle["sha256"]:
            raise ValueError(f"{case}: ZIP hash changed")
        with ZipFile(path) as opened:
            input_names = [r for r in expected if r.startswith("inputs/")]
            if opened.namelist() != input_names:
                raise ValueError(f"{case}: ZIP contains unexpected/missing input")
            for relative in input_names:
                if opened.read(relative) != expected[relative].read_bytes():
                    raise ValueError(f"{case}: ZIP entry bytes changed: {relative}")
    if case == "T04":
        release = manifest["held_release"]
        data = (target / release["relative_file"]).read_bytes()
        spec = json.loads((source / "case.json").read_bytes())["release_protocol"]
        if data != (source / "releases/rates.json").read_bytes() or sha(data) != release["sha256"]:
            raise ValueError("T04: held release byte/hash mismatch")
        if (target / "held-release/supplement-message.txt").read_bytes() != spec["response_text"].encode("utf-8"):
            raise ValueError("T04: supplement message changed")
    return {"case_id": case, "verified_initial_files": len(actual),
            "canonical_bytes_match": True, "no_answer_or_early_release": True,
            "product_submission_performed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="New directory outside the repository")
    parser.add_argument("--case", choices=(*CASE_IDS, "all"), default="all")
    parser.add_argument("--include-input-zip", action="store_true", help="Also prepare an optional ZIP; mode support remains unknown")
    parser.add_argument("--verify", action="store_true", help="Read-only verification of an existing preparation")
    args = parser.parse_args()
    destination = args.out.resolve()
    if within(destination, ROOT.resolve()):
        parser.error("--out must be outside the evaluation repository")
    selected = CASE_IDS if args.case == "all" else (args.case,)
    if args.verify:
        results = [verify_case(case, destination) for case in selected]
    else:
        if destination.exists():
            parser.error("--out already exists; choose a new directory or use --verify")
        destination.mkdir(parents=True)
        results = [prepare_case(case, destination, args.include_input_zip) for case in selected]
        write_json(destination / "preparation-index.json", {
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "schema": "web-upload-preparation-index-v1", "status": "prepared_not_submitted",
            "mode_availability_and_limits": "unknown_pending_live_ui_verification",
            "cases": results,
        })
        results = [verify_case(case, destination) for case in selected]
    print(json.dumps({"status": "verified_preparation_only", "cases": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
