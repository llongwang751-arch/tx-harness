"""Check published pilot manifests and independently recheck native artifacts.

This validates file integrity and artifacts, not provenance, release semantics,
manual judgments, or formal scores. Case IDs come from each public package.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_eval.core import evaluate, inside, inventory, read_json, sha256


def reported_product_failure(metadata):
    """Require both recorded declarations; an empty directory is not a failure claim."""
    return (metadata.get("product_side_failure") is True and
            metadata.get("execution_status") == "failed")


def verify_task_result(folder, case_id, metadata):
    """Recheck artifacts or an explicitly recorded product failure; skip diagnostics."""
    native_files = [p for p in (folder / "outputs").rglob("*")
                    if p.is_file() and p.name != "README.md"]
    product_failed = reported_product_failure(metadata)
    if not native_files and not product_failed:
        return None
    result = evaluate(ROOT / "cases" / case_id, folder / "outputs")
    verification_path = next((folder / name for name in
                              ("verification.json", "deterministic-verification.json")
                              if (folder / name).is_file()), None)
    if verification_path is None:
        raise ValueError(f"Missing task verification: {folder.name}")
    prior = read_json(verification_path)
    if (result["objective_score"] != prior["objective_score"] or
            result["all_checks_passed"] != prior["all_checks_passed"]):
        raise ValueError(f"Task result changed: {folder.name}")
    fields = ("id", "weight", "path", "passed", "sha256")
    current_checks = [{key: check.get(key) for key in fields}
                      for check in result["checks"]]
    recorded_checks = [{key: check.get(key) for key in fields}
                       for check in prior.get("checks", [])]
    if current_checks != recorded_checks:
        raise ValueError(f"Per-check result changed: {folder.name}")
    if (product_failed and "objective_score" in metadata and
            metadata["objective_score"] != result["objective_score"]):
        raise ValueError(f"Product failure metadata score changed: {folder.name}")
    return result


def main():
    packages = sorted((ROOT / "public/pilots").glob("*/manifest.json"))
    if not packages:
        raise ValueError("No published pilot packages")
    for manifest_path in packages:
        folder = manifest_path.parent
        manifest = read_json(manifest_path)
        declared = manifest.get("files", manifest.get("sha256", manifest))
        if not isinstance(declared, dict) or not declared:
            raise ValueError(f"Invalid manifest: {folder.name}")
        for name, digest in declared.items():
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"Invalid digest: {folder.name}/{name}")
            artifact = inside(folder, name)
            if not artifact.is_file() or sha256(artifact) != digest:
                raise ValueError(f"Digest mismatch: {folder.name}/{name}")
        actual = inventory(folder, exclude=("manifest.json",))
        if actual != declared:
            raise ValueError(f"Unregistered or missing file: {folder.name}")
        metadata_path = next((folder / name for name in
                              ("metadata.json", "run-metadata.json")
                              if (folder / name).is_file()), None)
        if metadata_path is None:
            raise ValueError(f"Missing pilot metadata: {folder.name}")
        metadata = read_json(metadata_path)
        case_id = metadata.get("case_id", metadata.get("case"))
        if case_id not in read_json(ROOT / "config/protocol.json")["case_ids"]:
            raise ValueError(f"Unknown case ID: {folder.name}")
        result = verify_task_result(folder, case_id, metadata)
        if result is not None:
            passed = sum(check["passed"] for check in result["checks"])
            failure_label = "product failed; " if reported_product_failure(metadata) else ""
            score_label = "task score" if reported_product_failure(metadata) else "artifact score"
            print(f"{folder.name}: manifest OK; {failure_label}{case_id} "
                  f"{passed}/{len(result['checks'])}; "
                  f"{score_label} {result['objective_score']}/60; pilot only")
        else:
            print(f"{folder.name}: manifest OK; no native deliverables; diagnostic, no task score")
    print(f"{len(packages)} pilot packages verified; this command does not compute formal results")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
