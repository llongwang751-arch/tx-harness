"""Fail-closed preparation and access checks for new T03-M / T05-M runs."""
from __future__ import annotations

import argparse
from hashlib import sha256 as digest
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness_eval.core import inside, inventory, load_case, read_json, sha256

CASES = ("T03-M", "T05-M")
REGISTER = "supplements/behavior-protocol-v2/run-register.json"
GATE_FILES = (
    "config/protocol.json",
    "harness_eval/core.py",
    "harness_eval/__main__.py",
    "scripts/behavior_preflight.py",
    "scripts/run_codex_pilot.py",
    "evaluation_v3/grader.py",
    "supplements/grader-v3/rules.json",
    "supplements/behavior-protocol-v1/protocol.json",
    "supplements/behavior-protocol-v1/gates.json",
)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def check_registration(commit, run_id, product, case):
    if not commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full committed prospective registration is required.")
    git("merge-base", "--is-ancestor", commit, "HEAD")
    raw = git("show", f"{commit}:{REGISTER}")
    if raw != (ROOT / REGISTER).read_bytes():
        raise ValueError("The working registration differs from the committed version.")
    register = read_json(ROOT / REGISTER)
    if register["registration_kind"] != "prospective":
        raise ValueError("Post-hoc registrations cannot authorize a new run.")
    if any(r["slot_id"] == run_id for r in read_json(
            ROOT / "supplements/behavior-protocol-v1/run-register.json")["slots"]):
        raise ValueError("A Week 5 slot ID cannot be reused.")
    if register["decision"] != "allow_registered_runs":
        raise ValueError("The prospective register has no approved execution.")
    rows = [r for r in register["slots"] if r["run_id"] == run_id]
    if len(rows) != 1 or (rows[0]["product_id"], rows[0]["case_id"]) != (product, case):
        raise ValueError("No unique committed registration matches this run, product and case.")
    source = ROOT / "cases" / case
    case_files = {f"cases/{case}/{name}" for name in inventory(source)}
    pinned_files = set(git("ls-tree", "-rz", "--name-only", commit, "--",
                           f"cases/{case}").decode().split("\0")) - {""}
    if case_files != pinned_files:
        raise ValueError("The current case inventory differs from the registration commit.")
    names = set(GATE_FILES) | case_files
    for name in sorted(names):
        if git("show", f"{commit}:{name}") != (ROOT / name).read_bytes():
            raise ValueError(f"Frozen file differs from registration commit: {name}")


def stage_workspace(case_dir, workspace, create):
    """Reject leftovers and validate the actual delivered tree after successful preparation."""
    if workspace.exists() or workspace.is_symlink():
        raise ValueError("Participant workspace already exists.")
    case, _ = load_case(case_dir)
    source = inside(case_dir, case["input_dir"])
    inputs = inventory(source)
    if not inputs:
        raise ValueError("Case has no input files.")
    expected = {f"inputs/{name}": digest for name, digest in inputs.items()}
    expected["prompt.md"] = sha256(inside(case_dir, case["prompt_file"]))
    create()
    if not (workspace / "inputs").is_dir() or not (workspace / "outputs").is_dir():
        raise ValueError("Prepared workspace is missing inputs/ or outputs/.")
    if next((workspace / "outputs").iterdir(), None) is not None:
        raise ValueError("Prepared output directory is not empty.")
    actual = inventory(workspace)
    if actual != expected:
        raise ValueError("Prepared input or prompt inventory differs from the frozen source.")
    return actual


def check_access(workspace, expected, protected_files):
    """Run with the participant's actual OS identity and confinement, before any submission."""
    if not protected_files:
        raise ValueError("Protected check targets are required.")
    for name, digest in expected.items():
        if sha256(inside(workspace, name)) != digest:
            raise ValueError(f"Participant cannot verify the staged input: {name}")
    for path in protected_files:
        try:
            with path.open("rb") as handle:
                handle.read(1)
        except PermissionError:
            continue
        except OSError as exc:
            raise ValueError(f"Access denial was not established for {path.name}: {type(exc).__name__}") from exc
        raise ValueError(f"Protected scoring data is readable: {path.name}")


def authorize_codex(run_id, case, commit):
    check_registration(commit, run_id, "codex", case)
    # A check in this evaluator process cannot stand in for the product sandbox.
    # Keep the launcher closed until the native adapter can make and bind that check.
    raise ValueError("No verified same-boundary access check is wired to this native launcher.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-closed-register", action="store_true", required=True)
    parser.add_argument("--incident", action="store_true")
    args = parser.parse_args(argv)
    try:
        register = read_json(ROOT / REGISTER)
        if register["registration_kind"] != "prospective" or register["decision"] != "artifact_audit_only" or register["slots"]:
            raise ValueError("The artifact-only decision requires an empty prospective register.")
        if args.incident:
            check_incident()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Preflight check failed: {exc}", file=sys.stderr)
        return 2
    print("Behavior preflight: artifact audit only; zero authorized runs.")
    return 0


def check_incident():
    record_path = "reports/week6/incidents/doubao-t03-m.json"
    added = git("log", "--diff-filter=A", "--format=%H", "HEAD", "--",
                record_path).decode().splitlines()
    if added and git("show", f"{added[-1]}:{record_path}") != (ROOT / record_path).read_bytes():
        raise ValueError("Incident record is sealed; add a separate dated addendum.")
    record = read_json(ROOT / record_path)
    old = record["evidence_commits"]["first_public_copy"]
    withdrawn = record["evidence_commits"]["withdrawal"]
    prefix = record["historical_public_path"]
    frozen_names = set(git("ls-tree", "-rz", "--name-only", old, "--",
                           prefix).decode().split("\0")) - {"", f"{prefix}/README.md"}
    declared = [f"{prefix}/{item['path']}" for item in record["files"]]
    if len(declared) != len(frozen_names) or set(declared) != frozen_names:
        raise ValueError("Incident does not cover the complete historical payload.")
    for item in record["files"]:
        data = git("show", f"{old}:{prefix}/{item['path']}")
        if len(data) != item["bytes"] or digest(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Incident blob differs: {item['path']}")
    if git("ls-tree", "-r", withdrawn, "--", prefix):
        raise ValueError("Withdrawn incident is still in the Week 5 public result path.")
    manifest = read_json(ROOT / "public/week5/manifest.json")
    if any(p["run_id"] == record["run_id"] for p in manifest["packages"]):
        raise ValueError("Withdrawn incident was re-admitted to scoring.")
    if (record["disposition"], record["output_source"], record["score"]) != ("invalid_run", "unproven", None):
        raise ValueError("Incident adjudication must remain source-unproven and unscored.")
    if git("show", f"{old}:{prefix}/outputs/bundle/announcement.md") != git(
            "show", f"{old}:cases/T03-M/expected/bundle/announcement.md"):
        raise ValueError("Claimed announcement byte equality was not reproduced.")


if __name__ == "__main__":
    sys.exit(main())
