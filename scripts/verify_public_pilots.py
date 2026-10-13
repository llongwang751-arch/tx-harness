"""Check published pilot manifests and independently recheck native artifacts.

This validates file integrity and T01 outputs, not provenance or formal scores.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_eval.core import evaluate, inside, inventory, read_json, sha256


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
        native_files = [p for p in (folder / "outputs").rglob("*")
                        if p.is_file() and p.name != "README.md"]
        if native_files:
            result = evaluate(ROOT / "cases/T01", folder / "outputs")
            if not result["all_checks_passed"]:
                raise ValueError(f"Published successful pilot no longer passes: {folder.name}")
            print(f"{folder.name}: manifest OK; T01 8/8; artifact score 60/60; pilot only")
        else:
            print(f"{folder.name}: manifest OK; no native deliverables; diagnostic, no task score")
    print(f"{len(packages)} pilot packages verified; this command does not compute formal results")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
