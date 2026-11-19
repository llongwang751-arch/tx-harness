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
FORMAL_REGISTER = "supplements/behavior-protocol-v3/run-register.json"
FORMAL_ACCESS = "public/behavior-formal/codex-t03m-access.json"
FORMAL_ACCESS_STDOUT = "public/behavior-formal/codex-t03m-sandbox.stdout.jsonl"
REVIEW = "reports/behavior-formal/review/T03-M.json"
GATE_FILES = (
    "config/protocol.json",
    "harness_eval/core.py",
    "harness_eval/__main__.py",
    "scripts/behavior_preflight.py",
    "scripts/behavior_codex_access.py",
    "scripts/probe_behavior_codex.py",
    "scripts/run_codex_pilot.py",
    "evaluation_v3/grader.py",
    "supplements/grader-v3/rules.json",
    "supplements/behavior-protocol-v1/protocol.json",
    "supplements/behavior-protocol-v1/gates.json",
    FORMAL_ACCESS,
    FORMAL_ACCESS_STDOUT,
)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def check_registration(commit, run_id, product, case):
    if not commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full committed prospective registration is required.")
    git("merge-base", "--is-ancestor", commit, "HEAD")
    raw = git("show", f"{commit}:{FORMAL_REGISTER}")
    if raw != (ROOT / FORMAL_REGISTER).read_bytes():
        raise ValueError("The working registration differs from the committed version.")
    register = read_json(ROOT / FORMAL_REGISTER)
    if register["registration_kind"] != "prospective":
        raise ValueError("Post-hoc registrations cannot authorize a new run.")
    if any(r["slot_id"] == run_id for r in read_json(
            ROOT / "supplements/behavior-protocol-v1/run-register.json")["slots"]):
        raise ValueError("A Week 5 slot ID cannot be reused.")
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
    return rows[0]


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


def check_independent_review(registration):
    path = ROOT / REVIEW
    if not path.is_file():
        raise ValueError("Formal submission awaits the independent T03-M judging spot-check.")
    if git("show", f"HEAD:{REVIEW}") != path.read_bytes():
        raise ValueError("The independent review must be recorded in Git before submission.")
    data = read_json(path)
    if (data.get('schema') != 'tx-harness/independent-judge-review/v1'
            or data.get('reviewed_commit') != registration['review_source_commit']
            or data.get('participated_in_grader_implementation') is not False):
        raise ValueError("The review lacks an independent role declaration or matching source version.")
    for field in ('reviewer_label', 'role', 'reviewed_on', 'environment', 'command', 'decision_basis'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"Independent review field is missing: {field}")
    checks = data.get('checks', {})
    if set(checks) != {'T03M-C01', 'T03M-C06'} or any(
            not checks[key].get('blind_observation') or not checks[key].get('recomputed_observation')
            for key in checks):
        raise ValueError("Independent review needs a blind judgment and a recomputation for both checks.")
    if data.get('decision') != 'accept_frozen_grader_with_documented_limits':
        raise ValueError("Resolve the recorded judging disagreement before using this frozen protocol.")
    return {'git_commit': git('rev-parse', 'HEAD').decode().strip(), 'sha256': sha256(path)}


def authorize_codex(run_id, case, commit, *, attempt=1, model=None):
    row = check_registration(commit, run_id, 'codex', case)
    if row['attempt'] != attempt or row['requested_model'] != model:
        raise ValueError('Attempt or requested model differs from the prospective registration.')
    check_formal_readiness()
    review = check_independent_review(row)
    return row, review


def check_formal_readiness():
    from scripts.behavior_codex_access import protected_files, validate_observation

    register = read_json(ROOT / FORMAL_REGISTER)
    if register.get('registration_kind') != 'prospective' or len(register['slots']) != 1:
        raise ValueError('Expected one prospectively registered Codex CLI case.')
    row, = register['slots']
    if (row.get('product_id'), row.get('case_id'), row.get('attempt')) != ('codex', 'T03-M', 1):
        raise ValueError('Unexpected scope: only Codex T03-M attempt 1 is registered.')
    proof = read_json(ROOT / FORMAL_ACCESS)
    stdout = ROOT / FORMAL_ACCESS_STDOUT
    if sha256(stdout) != proof['stdout_sha256'] or read_json(stdout) != proof['observation']:
        raise ValueError('The public native sandbox output differs from the access receipt.')
    case_dir = ROOT / 'cases/T03-M'
    expected = {'prompt.md': sha256(case_dir / 'prompt.md'), **{
        f'inputs/{name}': digest_value for name, digest_value in inventory(case_dir / 'inputs').items()}}
    targets = protected_files('T03-M')
    validate_observation(proof['observation'], expected, targets)
    if proof['protected_files'] != {label: {'path': path.relative_to(ROOT).as_posix(), 'host_sha256': sha256(path)}
                                    for label, path in targets.items()}:
        raise ValueError('Protected-file receipt no longer matches the registered files.')
    if (proof['exit_code'] != 0 or proof['business_task_submitted'] is not False
            or proof['codex_version'] != row['cli_version']
            or proof['executable_sha256'] != row['cli_binary_sha256']):
        raise ValueError('Access receipt differs from the registered binary or task boundary.')
    if proof['native_turn']['exit_code'] != 0 or proof['native_turn']['matched_shell_input_sha256'] != expected:
        raise ValueError('Native tool positive observation differs from the registered files.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-closed-register", action="store_true")
    mode.add_argument("--check-formal-readiness", action="store_true")
    parser.add_argument("--incident", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_closed_register:
            register = read_json(ROOT / REGISTER)
            if register["registration_kind"] != "prospective" or register["decision"] != "artifact_audit_only" or register["slots"]:
                raise ValueError("The historical artifact-only decision requires an empty prospective register.")
        else:
            check_formal_readiness()
        if args.incident:
            check_incident()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Preflight check failed: {exc}", file=sys.stderr)
        return 2
    if args.check_closed_register:
        print("Behavior preflight: historical artifact-only registration intact.")
    else:
        print("Behavior preflight: one candidate and its access receipt match; this check does not certify judging.")
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
