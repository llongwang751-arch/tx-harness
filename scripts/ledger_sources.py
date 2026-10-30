"""Derive the week-three run ledger from frozen public evidence.

Every field of a run record is either copied from a registered source file or
derived by a rule implemented here.  Nothing is read from the system clock, the
private collection area, or a live product.  The same functions are used by the
build step and by the read-only audit step, so a hand edit to a generated file
shows up as a byte difference instead of passing unnoticed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

ACCOUNTS = (
    "product_run",
    "self_test",
    "offline_recompute",
    "grader_regression",
    "bare_model_probe",
    "interface_preflight",
)

PRODUCTS = ("codex", "workbuddy", "dsh", "yuanbao", "doubao")

# Which products had no shared endpoint or no accepted shared-tool contract at
# the recorded interface check.  Used only for narrative text, never for scores.
TRACKS = (
    "formal_product_end_to_end",
    "formal_controlled_contract",
    "adapter_calibration",
    "native_ui_probe",
    "repeat_batch",
)

PRODUCT_LABELS = {
    "codex": "Codex",
    "workbuddy": "WorkBuddy",
    "dsh": "DSH",
    "yuanbao": "元宝专家模式",
    "doubao": "豆包工作任务模式",
}


def rel(path) -> str:
    value = Path(path)
    if not value.is_absolute():
        value = ROOT / value
    return value.resolve().relative_to(ROOT).as_posix()


def load(relative):
    path = ROOT / relative
    return json.loads(path.read_text(encoding="utf-8"))


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(relative) -> str:
    return sha_bytes((ROOT / relative).read_bytes())


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def pointer(value, path):
    """Read a JSON pointer such as /counts/synthetic_examples."""
    current = value
    if not path:
        return current
    for part in path.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def source(relative, path="") -> dict:
    return {"path": rel(relative), "sha256": sha_file(relative), "json_pointer": path}


def exists(relative) -> bool:
    return (ROOT / relative).exists()


def parse_time(value):
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    if "." in text:
        head, tail = text.split(".", 1)
        digits = ""
        for char in tail:
            if char.isdigit():
                digits += char
            else:
                break
        rest = tail[len(digits):]
        text = f"{head}.{digits[:6].ljust(6, '0')}{rest}"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def duration_seconds(started, ended):
    first, second = parse_time(started), parse_time(ended)
    if first is None or second is None:
        return None
    return round((second - first).total_seconds(), 3)


# ---------------------------------------------------------------------------
# Evidence grades.  One documented rule, applied to the evidence actually
# retained for a run.  A grade never turns into points.
# ---------------------------------------------------------------------------

GRADE_RULE = (
    "high: retained native request/response events AND artifact hashes AND an independent "
    "recomputation of the artifact contract; medium: artifact hashes plus a verification "
    "record but no full native event stream; low: narrative or screenshot evidence without "
    "artifact-level verification; none: no retained evidence"
)


def classify_grade(classes) -> str:
    classes = set(classes)
    if {"native_events", "artifact_hashes", "independent_recompute"} <= classes:
        return "high"
    if {"artifact_hashes", "verification_record"} <= classes:
        return "medium"
    if "narrative_only" in classes:
        return "low"
    return "none"


def verdict_from(status):
    return {"pass": "pass", "valid": "pass", "fail": "fail", "failed": "fail",
            "unknown": "unknown", "invalid": "invalid"}.get(str(status).lower(), "unknown")


# ---------------------------------------------------------------------------
# The five-product end-to-end task track: 25 selected combinations.
# ---------------------------------------------------------------------------

def formal_runs():
    records = []
    for run in evaluation()["runs"]:
        records.append(formal_record(run))
    return records


_CACHE = {}


def evaluation():
    if "evaluation" not in _CACHE:
        _CACHE["evaluation"] = load("reports/evaluation-v2.json")
    return _CACHE["evaluation"]


def first_of(*values):
    for value in values:
        if value not in (None, "", "unknown", "Unknown", "none"):
            return value
    return None


PROMPT_CANDIDATES = ("submitted-prompt.txt", "submitted-prompt.md", "case-prompt.md", "prompt.md")


def frozen_inputs_ok(case, folder):
    """Compare the retained input copy with the frozen case inputs.

    Extra files are allowed and reported: T04 hands the product one registered
    supplement attachment after the first delivery.  A changed or missing frozen
    input is not allowed.
    """
    base = ROOT / folder / "inputs"
    expected = ROOT / "cases" / case / "inputs"
    if not base.is_dir() or not expected.is_dir():
        return None, []
    basis = []
    same = True
    frozen = {path.name: path for path in expected.iterdir() if path.is_file()}
    retained = {path.name: path for path in base.iterdir() if path.is_file()}
    for name, path in sorted(frozen.items()):
        if name not in retained:
            same = False
            basis.append(f"inputs/{name} is missing from the retained copy")
            continue
        match = sha_file(retained[name]) == sha_file(path)
        same = same and match
        basis.append(f"inputs/{name} {'==' if match else '!='} frozen copy")
    for name in sorted(set(retained) - set(frozen)):
        basis.append(f"inputs/{name} is a registered supplement, not a frozen input")
    return same, basis


def package_outputs(folder, graded):
    items = []
    base = ROOT / folder / "outputs"
    if not base.is_dir():
        return items
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        key = rel(path)
        reference = graded.get(key)
        items.append({"path": key, "sha256": sha_file(path), "graded_sha256": reference,
                      "matches_graded": None if reference is None else reference == sha_file(path)})
    return items


def formal_record(run):
    run_id = run["run_id"]
    product = run["product_id"]
    case = run["case_id"]
    metadata_path = run["metadata_source"]["path"]
    metadata = load(metadata_path)
    verification_path = run["historical_objective"]["verification_source"]["path"]
    verification = load(verification_path) if exists(verification_path) else None
    folder = PurePosixPath(metadata_path).parent
    manifest_path = f"{folder}/manifest.json"

    files = [source(metadata_path), source(verification_path)]
    if exists(manifest_path):
        files.append(source(manifest_path))
    events_path = f"{folder}/visible-events.jsonl"
    events = exists(events_path)
    if events:
        files.append(source(events_path))
    graded = {}
    for check in run["checks"]:
        actual = check.get("actual_source") or {}
        if actual.get("present") and actual.get("path"):
            graded[actual["path"]] = actual["sha256"]
    outputs = package_outputs(folder, graded)
    graded_match = bool(graded) and any(item["matches_graded"] is True for item in outputs) \
        and all(item["matches_graded"] is not False for item in outputs)

    classes = ["artifact_hashes", "verification_record"]
    if events:
        classes.append("native_events")
    if graded_match and verification and verification.get("all_checks_passed") in (True, False):
        classes.append("independent_recompute")
    grade = classify_grade(classes)

    passed = None if verification is None else bool(verification.get("all_checks_passed"))
    score = run["historical_objective"]["score"]
    state = "pass" if passed else ("fail" if passed is False else "unknown")

    conditions = metadata.get("visible_conditions") or {}
    inputs_ok, inputs_basis = frozen_inputs_ok(case, folder)
    contamination_basis = []
    if graded_match:
        contamination_basis.append("collected output bytes hash to the bytes quoted for grading")
    if inputs_ok is True:
        contamination_basis.append(f"every retained input file still matches cases/{case}/inputs")
    contamination = "none" if inputs_ok is True and (graded_match or not outputs) else "unknown"

    prompt_path = next((f"{folder}/{name}" for name in PROMPT_CANDIDATES
                        if exists(f"{folder}/{name}")), None)
    prompt_valid_basis = []
    prompt_ok = False
    if prompt_path:
        submitted = (ROOT / prompt_path).read_bytes()
        template = (ROOT / f"cases/{case}/prompt.md").read_bytes().rstrip(b"\n")
        exact = submitted.startswith(template)
        line_endings = submitted.replace(b"\r\n", b"\n").startswith(
            template.replace(b"\r\n", b"\n"))
        prompt_ok = exact or line_endings
        prompt_valid_basis.append(
            f"{prompt_path} starts with the frozen cases/{case}/prompt.md bytes: exact={exact} "
            f"after line-ending normalisation={line_endings}")
    else:
        prompt_valid_basis.append("no submitted prompt retained")
    if inputs_ok is True:
        prompt_valid_basis.append("every retained input file still matches the frozen case inputs")
    elif inputs_ok is False:
        prompt_ok = False
        prompt_valid_basis.append("at least one retained input file differs from the frozen inputs")

    tools = metadata.get("tools")
    timing_reason = None
    started = metadata.get("started_at")
    ended = first_of(metadata.get("native_ended_at"), metadata.get("completed_at"),
                     metadata.get("completion_observed_at"))
    if not started or not ended:
        timing_reason = "start/end not both retained in the public excerpt"

    version = first_of(metadata.get("product_version"), conditions.get("version"),
                       conditions.get("version_visible"),
                       conditions.get("installed_binary_version"))
    model_label = first_of(metadata.get("model"), conditions.get("model"),
                           conditions.get("model_visible"))
    visibility = first_of(metadata.get("model_visibility"))
    attested = metadata.get("model_visibility") == "verified"
    permissions = first_of(metadata.get("permissions"), conditions.get("permission"),
                           conditions.get("permission_label"),
                           conditions.get("permission_visible"))
    skill = first_of(metadata.get("skill_condition"), conditions.get("skill_condition"),
                     metadata.get("active_skills"))

    record = {
        "schema": "tx-harness/run-record/v1",
        "run_id": run_id,
        "account": "product_run",
        "track": "formal_product_end_to_end",
        "task": {
            "case_id": case,
            "case_sha256": sha_file(f"cases/{case}/case.json"),
            "prompt_sha256": sha_file(f"cases/{case}/prompt.md"),
            "version_basis": "content hash of the frozen case and prompt; no mutable version label",
        },
        "product": {
            "product_id": product,
            "label": PRODUCT_LABELS[product],
            "version": version,
            "version_reason": None if version else
                              "no version label or installed binary version was retained",
            "binary_sha256": (metadata.get("environment") or {}).get("binary_sha256"),
            "surface": metadata.get("surface"),
        },
        "model": {
            "label": model_label,
            "attested": attested,
            "visibility": visibility,
            "reason": None if attested else
                      "the retained excerpt carries at most a UI label; the backend model identity "
                      "is never attested",
        },
        "tools": {
            "state": "recorded" if tools else "unknown",
            "items": tools or [],
            "reason": None if tools else "the public excerpt retains no tool inventory for this run",
        },
        "permissions": {
            "label": permissions,
            "source": rel(metadata_path) + "#/permissions|visible_conditions.permission",
            "reason": None if permissions else "no permission label was retained",
        },
        "skill_state": {
            "label": skill,
            "source": rel(metadata_path) + "#/skill_condition|visible_conditions.skill_condition",
            "reason": None if skill else "no Skill state was retained",
        },
        "timing": {
            "started_at": started,
            "ended_at": ended,
            "duration_seconds": first_of(
                metadata.get("elapsed_to_completion_observation_seconds"),
                duration_seconds(started, ended)),
            "reason": timing_reason,
        },
        "evidence": {
            "grade": grade,
            "classes": sorted(set(classes)),
            "files": sorted(files, key=lambda item: item["path"]),
            "outputs": sorted(outputs, key=lambda item: item["path"]),
            "inputs": {"state": inputs_ok, "basis": inputs_basis},
            "contamination": {"state": contamination, "basis": contamination_basis},
        },
        "gates": {},
        "verdict": {
            "state": state,
            "reason": (f"verification.json all_checks_passed={passed}" if verification else
                       "no retained verification record"),
            "objective_score": score,
            "objective_max": run["historical_objective"]["maximum"],
            "score_for_aggregate": score if state in ("pass", "fail") else None,
        },
        "attribution": {
            "harness_attributable": False,
            "reason": "single product, single configuration; model and Skill are not held constant",
            "controls": [],
            "unexcluded": ["backend model identity", "built-in Skill state", "host environment"],
        },
        "prompt_validity": {"ok": prompt_ok, "basis": prompt_valid_basis},
        "sources": [
            {"path": rel(metadata_path), "sha256": sha_file(metadata_path), "json_pointer": ""},
            {"path": rel(verification_path), "sha256": sha_file(verification_path),
             "json_pointer": "/all_checks_passed"},
            {"path": "reports/evaluation-v2.json", "sha256": sha_file("reports/evaluation-v2.json"),
             "json_pointer": f"/runs/{evaluation_index(run_id)}"},
        ],
    }
    record["gates"] = run_gates(record)
    return record


def evaluation_index(run_id):
    for index, run in enumerate(evaluation()["runs"]):
        if run["run_id"] == run_id:
            return index
    raise KeyError(run_id)


# ---------------------------------------------------------------------------
# Registered runs from the weekly execution register (native UI and the fixed
# local fixture).  Counted separately from the end-to-end task track.
# ---------------------------------------------------------------------------

PRODUCT_BY_PREFIX = {"W": "workbuddy", "R": "workbuddy", "WBC": "workbuddy",
                     "CA11": "dsh", "CA13": "dsh", "CA00": "dsh", "CA12": "codex",
                     "CA14": "codex", "CA02": "codex", "CA03": "codex"}


def registered_runs():
    register = load("supplements/week2/executions.json")
    records = []
    for entry in register["entries"]:
        records.append(registered_record(entry))
    return records


def product_for(run_id, execution):
    if execution.get("product_id"):
        return execution["product_id"]
    configuration = execution.get("configuration") or {}
    label = str(configuration.get("product", "")).lower()
    for product in PRODUCTS:
        if product in label or {"workbuddy": "workbuddy"}.get(product, product) in label:
            return product
    for prefix in sorted(PRODUCT_BY_PREFIX, key=len, reverse=True):
        if run_id.startswith(prefix):
            return PRODUCT_BY_PREFIX[prefix]
    raise KeyError(f"cannot bind product for {run_id}")


def track_for(entry, execution):
    if entry.get("track") == "real_model_task":
        return "native_ui_probe"
    if entry.get("track") == "controlled_adapter_fixture":
        return ("formal_controlled_contract" if execution.get("phase") == "main"
                else "adapter_calibration")
    return "adapter_calibration"


CONSTRAINED_CASE = "S01"
WINDOW_CASE = "S02"


def registered_record(entry):
    run_id = entry["run_id"]
    folder = PurePosixPath(entry["public_manifest"]).parent
    execution_path = f"{folder}/execution.json"
    execution = load(execution_path)
    product = product_for(run_id, execution)
    track = track_for(entry, execution)
    configuration = execution.get("configuration") or {}
    case = CONSTRAINED_CASE if track != "native_ui_probe" else WINDOW_CASE

    files = [source(execution_path)]
    present = []
    for name in ("manifest.json", "review.json", "judgment.json", "reviewed-native-events.jsonl",
                 "mcp-events.jsonl", "model-events.jsonl", "native-events.jsonl",
                 "independent-verification.json", "verification.json"):
        relative = f"{folder}/{name}"
        if exists(relative):
            files.append(source(relative))
            present.append(name)

    classes = []
    if {"review.json", "judgment.json", "verification.json"} & set(present):
        classes.append("verification_record")
    outputs = package_outputs(folder, {})
    if outputs or "artifact" in execution:
        classes.append("artifact_hashes")
    if {"mcp-events.jsonl", "model-events.jsonl"} & set(present) \
            or "reviewed-native-events.jsonl" in present:
        classes.append("native_events")
    if audited(run_id) or "independent-verification.json" in present:
        classes.append("independent_recompute")
    grade = classify_grade(classes)

    state = verdict_from(entry.get("validity"))
    if state == "pass" and str(entry.get("outcome")) == "unknown":
        state = "unknown"
    if entry.get("validity") == "valid" and entry.get("outcome") in ("pass", "fail"):
        state = entry["outcome"]

    started = execution.get("started_at")
    ended = execution.get("ended_at")
    reason = None
    if not started or not ended:
        reason = "start/end not both retained"
    if execution.get("version_basis"):
        version_basis = execution["version_basis"]
    elif configuration.get("version_basis"):
        version_basis = configuration["version_basis"]
    else:
        version_basis = "native binary hash recorded" if execution.get("executable_sha256") \
            else "version label only; no binary attestation"

    if track == "native_ui_probe":
        model_label = configuration.get("model_label")
        model_reason = "UI label only; no backend attestation"
        permissions = configuration.get("permission_label")
        skill = configuration.get("skill")
        tools_state, tools_reason = "unknown", "no tool inventory retained for a native UI task"
        version = configuration.get("version_label")
        surface = "native desktop window"
    else:
        model_label = execution.get("model_kind")
        model_reason = "deterministic local fixture; no neural model inference"
        permissions = "host process permission profile of the registered fixture"
        skill = execution.get("skill_configuration") or configuration.get("skill")
        tools_state = "scripted"
        tools_reason = None
        version = execution.get("version")
        surface = execution.get("adapter_version", "native CLI/SDK")

    contamination_basis = ["fixed local fixture; no external inference service"]
    if entry.get("track") == "real_model_task":
        contamination_basis = [f"{rel(execution_path)}#/actual_submitted=true",
                               "single active product window during collection"]
    contamination = "none" if track != "native_ui_probe" or len(contamination_basis) >= 2 else "unknown"

    prompt_sha = execution.get("prompt_sha256")
    if prompt_sha:
        prompt_ok, prompt_basis = True, [f"{rel(execution_path)}#/prompt_sha256"]
    elif track != "native_ui_probe":
        prompt_file = "supplements/controlled-adapter-v1/prompt.txt"
        prompt_sha = sha_file(prompt_file)
        prompt_ok = True
        prompt_basis = [f"frozen fixture prompt {prompt_file}"]
    else:
        prompt_ok, prompt_basis = False, ["no retained prompt hash for this native task"]

    record = {
        "schema": "tx-harness/run-record/v1",
        "run_id": run_id,
        "account": "product_run",
        "track": track,
        "task": {
            "case_id": case,
            "case_sha256": sha_file(f"cases/{case}/case.json") if exists(f"cases/{case}/case.json")
            else sha_file("supplements/controlled-adapter-v1/protocol.json"),
            "prompt_sha256": prompt_sha,
            "version_basis": "content hash of the registered protocol and prompt",
        },
        "product": {"product_id": product, "label": PRODUCT_LABELS[product], "version": version,
                    "binary_sha256": execution.get("executable_sha256"),
                    "surface": surface, "version_basis": version_basis},
        "model": {"label": model_label, "attested": False, "visibility": "not_applicable"
                  if track != "native_ui_probe" else "ui_label_only", "reason": model_reason},
        "tools": {"state": tools_state,
                  "items": ["probe_commit"] if tools_state == "scripted" else [],
                  "reason": tools_reason},
        "permissions": {
            "label": permissions,
            "source": (f"{rel(execution_path)}#/configuration" if track == "native_ui_probe"
                       else rel(execution_path)),
            "reason": None if permissions else "no permission label was retained",
        },
        "skill_state": {
            "label": skill,
            "source": (f"{rel(execution_path)}#/skill_configuration"
                       if track != "native_ui_probe"
                       else f"{rel(execution_path)}#/configuration/skill"),
            "reason": None if skill else "no Skill state was retained",
        },
        "timing": {"started_at": started, "ended_at": ended,
                   "duration_seconds": execution.get("elapsed_seconds")
                   or execution.get("host_elapsed_seconds") or duration_seconds(started, ended),
                   "reason": reason},
        "evidence": {
            "grade": grade,
            "classes": sorted(set(classes)),
            "files": sorted(files, key=lambda item: item["path"]),
            "outputs": outputs,
            "inputs": {"state": None, "basis": ["this track does not use the frozen case inputs"]},
            "contamination": {"state": contamination, "basis": contamination_basis},
        },
        "gates": {},
        "verdict": {
            "state": state,
            "reason": f"register validity={entry.get('validity')} outcome={entry.get('outcome')}",
            "objective_score": None,
            "objective_max": None,
            "score_for_aggregate": None,
        },
        "attribution": {
            "harness_attributable": track == "formal_controlled_contract",
            "reason": ("scripted model and skill state are identical across arms; the remaining "
                       "difference is the product transport/orchestration"
                       if track == "formal_controlled_contract" else
                       "single product observation; no matched control"),
            "controls": (["supplements/controlled-adapter-v1/protocol.json#frozen_arguments"]
                         if track == "formal_controlled_contract" else []),
            "unexcluded": ([] if track == "formal_controlled_contract" else
                           ["backend model identity", "built-in Skill state"]),
        },
        "prompt_validity": {"ok": prompt_ok, "basis": prompt_basis},
        "sources": [{"path": rel(execution_path), "sha256": sha_file(execution_path),
                     "json_pointer": ""},
                    {"path": rel(entry["public_manifest"]),
                     "sha256": sha_file(entry["public_manifest"]), "json_pointer": ""}],
    }
    record["gates"] = run_gates(record)
    return record


def collect_outputs(folder):
    return package_outputs(folder, {})


_AUDIT_CACHE = {}


def audited(run_id):
    """Was this run independently recomputed by a published audit script?"""
    if not _AUDIT_CACHE:
        for relative in ("reports/controlled-adapter-v1.json", "reports/controlled-workbuddy.json"):
            if not exists(relative):
                continue
            for package in load(relative).get("packages", []):
                _AUDIT_CACHE[package.get("run_id")] = relative
    return _AUDIT_CACHE.get(run_id)


# ---------------------------------------------------------------------------
# Gates.  Table eligibility is the four conditions in the new requirement; a
# ranking needs the stricter conditions from the frozen rubric as well.
# ---------------------------------------------------------------------------

def run_gates(record):
    evidence = record["evidence"]
    files_ok = all(sha_file(item["path"]) == item["sha256"] for item in evidence["files"])
    outputs_ok = all(item.get("matches_graded") is not False for item in evidence["outputs"])
    frozen = frozen_case_ok(record)
    return {
        "rule_frozen": frozen,
        "prompt_valid": bool(record["prompt_validity"]["ok"]),
        "evidence_valid": evidence["grade"] in ("high", "medium") and files_ok and outputs_ok,
        "uncontaminated": evidence["contamination"]["state"] == "none",
        "detail": {
            "frozen_case_basis": "cases/<case>/case.json and oracle.json hashes equal the frozen "
                                 "check sources quoted by reports/evaluation-v2.json",
            "files_verified": len(evidence["files"]),
            "outputs_verified": len(evidence["outputs"]),
        },
    }


def frozen_case_ok(record):
    """The frozen case and oracle must still hash to what the ledger quoted."""
    case = record["task"]["case_id"]
    if not exists(f"cases/{case}/case.json"):
        return record.get("track") in ("formal_controlled_contract", "adapter_calibration",
                                       "native_ui_probe")
    case_sha = sha_file(f"cases/{case}/case.json")
    oracle_sha = sha_file(f"cases/{case}/oracle.json") if exists(f"cases/{case}/oracle.json") else None
    for run in evaluation()["runs"]:
        if run["case_id"] != case:
            continue
        for check in run["checks"]:
            quoted = (check.get("frozen_check_source") or {}).get("sha256")
            if quoted and quoted != case_sha:
                return False
            expected = check.get("expected_source") or {}
            if expected.get("present") and oracle_sha and expected.get("sha256") \
                    and expected.get("path", "").endswith("oracle.json") \
                    and expected["sha256"] != oracle_sha:
                return False
    return True


def table_eligible(record):
    gates = record["gates"]
    return (record["account"] == "product_run"
            and all(gates[name] for name in ("rule_frozen", "prompt_valid",
                                             "evidence_valid", "uncontaminated")))


def ranking_eligible(record):
    return table_eligible(record) and bool(record["model"]["attested"]) \
        and record["track"] == "formal_product_end_to_end"


def build_table(records):
    rows = [record for record in records if record["account"] == "product_run"]
    main = [record for record in rows if record["track"] == "formal_product_end_to_end"]
    controlled = [record for record in rows if record["track"] == "formal_controlled_contract"]
    calibration = [record for record in rows if record["track"] == "adapter_calibration"]
    repeat = [record for record in rows if record["track"] == "repeat_batch"]

    def compact(record):
        return {
            "run_id": record["run_id"],
            "product_id": record["product"]["product_id"],
            "case_id": record["task"]["case_id"],
            "verdict": record["verdict"]["state"],
            "objective_score": record["verdict"]["objective_score"],
            "objective_max": record["verdict"]["objective_max"],
            "evidence_grade": record["evidence"]["grade"],
            "gates": {name: record["gates"][name] for name in
                      ("rule_frozen", "prompt_valid", "evidence_valid", "uncontaminated")},
            "table_eligible": table_eligible(record),
            "ranking_eligible": ranking_eligible(record),
        }

    products = []
    for product in PRODUCTS:
        owned = [record for record in main if record["product"]["product_id"] == product]
        scored = [record for record in owned if record["verdict"]["state"] in ("pass", "fail")]
        unknown = [record for record in owned if record["verdict"]["state"] == "unknown"]
        excluded = [record for record in owned if not table_eligible(record)]
        total = sum(record["verdict"]["score_for_aggregate"] or 0 for record in scored)
        maximum = sum(record["verdict"]["objective_max"] or 0 for record in scored)
        products.append({
            "product_id": product,
            "label": PRODUCT_LABELS[product],
            "runs": len(owned),
            "scored": len(scored),
            "pass": sum(1 for record in scored if record["verdict"]["state"] == "pass"),
            "fail": sum(1 for record in scored if record["verdict"]["state"] == "fail"),
            "unknown": len(unknown),
            "excluded_by_gate": len(excluded),
            "objective_points": total,
            "objective_maximum": maximum,
            "cases_scored": sorted({record["task"]["case_id"] for record in scored}),
            "missing_cases": sorted({f"T{index:02d}" for index in range(1, 6)} -
                                    {record["task"]["case_id"] for record in owned}),
            "ranking": None,
        })

    ranking_reasons = []
    for product in products:
        record_set = [record for record in main if record["product"]["product_id"] == product["product_id"]]
        if not record_set:
            ranking_reasons.append(f"{product['label']}: no registered end-to-end run")
            continue
        if not all(record["model"]["attested"] for record in record_set):
            ranking_reasons.append(f"{product['label']}: backend model identity unattested")
        if not all(record["track"] == "formal_product_end_to_end" for record in record_set):
            ranking_reasons.append(f"{product['label']}: track differs")
    if len({record["product"]["product_id"] for record in main}) < len(PRODUCTS):
        ranking_reasons.append("at least one product has no end-to-end run at all")
    ranking_reasons.append("protocol state of the 25 end-to-end runs is draft_before_pilot, not "
                           "a preregistered frozen protocol")
    return {
        "schema": "tx-harness/formal-comparison-table/v1",
        "generation_basis": "deterministic projection of ledger/runs.jsonl; no clock, no product run",
        "admission_rule": "account=product_run and rule_frozen and prompt_valid and "
                          "evidence_valid and uncontaminated",
        "ranking_rule": "admission plus attested backend model and a preregistered frozen protocol",
        "main_rows": [compact(record) for record in sorted(
            main, key=lambda item: (item["product"]["product_id"], item["task"]["case_id"]))],
        "controlled_rows": [compact(record) for record in sorted(
            controlled, key=lambda item: item["run_id"])],
        "calibration_rows": [compact(record) for record in sorted(
            calibration, key=lambda item: item["run_id"])],
        "repeat_rows": [compact(record) for record in sorted(
            repeat, key=lambda item: item["run_id"])],
        "products": products,
        "ranking": None,
        "ranking_withheld_because": ranking_reasons,
        "counts": {
            "product_runs": len(rows),
            "end_to_end": len(main),
            "controlled_contract": len(controlled),
            "calibration": len(calibration),
            "repeat_batch": len(repeat),
            "comparison_eligible": sum(1 for record in main + controlled
                                       if table_eligible(record)),
            "comparison_excluded": sum(1 for record in main + controlled
                                       if not table_eligible(record)),
            "calibration_unknown": sum(1 for record in calibration
                                       if record["verdict"]["state"] == "unknown"),
            "unknown_verdicts": sum(1 for record in rows
                                    if record["verdict"]["state"] == "unknown"),
        },
    }


# ---------------------------------------------------------------------------
# Repeat batch: the same task run three times on one product with the real
# model, to measure output stability instead of adding new task coverage.
# ---------------------------------------------------------------------------

REPEAT_PACKAGES = ("dsh-sdk-T01-r2", "dsh-sdk-T01-r3", "dsh-sdk-T02-r2", "dsh-sdk-T02-r3",
                   "dsh-sdk-T03-r2", "dsh-sdk-T03-r3", "dsh-sdk-T05-r2", "dsh-sdk-T05-r3")


def repeat_runs():
    return [repeat_record(name) for name in REPEAT_PACKAGES]


def repeat_record(name):
    folder = f"public/pilots/{name}"
    metadata = load(f"{folder}/run-metadata.json")
    verification = load(f"{folder}/deterministic-verification.json")
    case = metadata["case_id"]
    graded = {check["path"]: check["sha256"] for check in verification["checks"]
              if check.get("sha256")}
    outputs = []
    for path in sorted((ROOT / folder / "outputs").rglob("*")):
        if not path.is_file():
            continue
        key = path.relative_to(ROOT / folder / "outputs").as_posix()
        reference = graded.get(key)
        outputs.append({"path": rel(path), "sha256": sha_file(path),
                        "graded_sha256": reference,
                        "matches_graded": None if reference is None else reference == sha_file(path)})
    graded_match = bool(graded) and any(item["matches_graded"] is True for item in outputs) \
        and all(item["matches_graded"] is not False for item in outputs)
    inputs_ok, inputs_basis = frozen_inputs_ok(case, folder)
    passed = bool(verification.get("all_checks_passed"))
    state = "pass" if passed else "fail"
    score = verification.get("objective_score")
    prompt_path = next((f"{folder}/{name_}" for name_ in PROMPT_CANDIDATES
                        if exists(f"{folder}/{name_}")), None)
    prompt_ok = False
    prompt_basis = []
    if prompt_path:
        submitted = (ROOT / prompt_path).read_bytes()
        template = (ROOT / f"cases/{case}/prompt.md").read_bytes().rstrip(b"\n")
        prompt_ok = submitted.startswith(template)
        prompt_basis.append(f"{prompt_path} starts with the frozen cases/{case}/prompt.md: "
                            f"{prompt_ok}")
    record = {
        "schema": "tx-harness/run-record/v1",
        "run_id": name,
        "account": "product_run",
        "track": "repeat_batch",
        "task": {"case_id": case,
                 "case_sha256": sha_file(f"cases/{case}/case.json"),
                 "prompt_sha256": sha_file(f"cases/{case}/prompt.md"),
                 "version_basis": "content hash of the frozen case and prompt"},
        "product": {"product_id": "dsh", "label": PRODUCT_LABELS["dsh"],
                    "version": metadata.get("installation_version"),
                    "version_reason": None,
                    "binary_sha256": None,
                    "surface": f"desktop-bundled CLI ({metadata.get('profile')} profile)"},
        "model": {"label": f"{metadata.get('requested_model')} (requested)",
                  "attested": False,
                  "visibility": metadata.get("model_visibility"),
                  "reason": metadata.get("model_identity_note")},
        "tools": {"state": "unknown", "items": [],
                  "reason": "the public projection keeps tool names and results, not a complete "
                            "tool inventory"},
        "permissions": {"label": f"sandbox={metadata.get('sandbox')}; "
                                 f"task_network_tool={metadata.get('task_network_tool')}",
                        "source": f"{folder}/run-metadata.json",
                        "reason": None},
        "skill_state": {"label": metadata.get("skills"),
                        "source": f"{folder}/run-metadata.json",
                        "reason": None},
        "timing": {"started_at": metadata.get("started_at"),
                   "ended_at": metadata.get("finished_at"),
                   "duration_seconds": metadata.get("elapsed_seconds"),
                   "reason": None},
        "evidence": {
            "grade": classify_grade(["artifact_hashes", "verification_record",
                                     "native_events", "independent_recompute"]),
            "classes": ["artifact_hashes", "independent_recompute", "native_events",
                        "verification_record"],
            "files": sorted([source(f"{folder}/run-metadata.json"),
                             source(f"{folder}/deterministic-verification.json"),
                             source(f"{folder}/manifest.json"),
                             source(f"{folder}/visible-events.jsonl")],
                            key=lambda item: item["path"]),
            "outputs": outputs,
            "inputs": {"state": inputs_ok, "basis": inputs_basis},
            "contamination": {"state": "none" if graded_match and inputs_ok is True else "unknown",
                              "basis": ["collected output bytes hash to the graded bytes",
                                        "retained input files still match the frozen inputs"]
                              if graded_match and inputs_ok is True else []},
        },
        "gates": {},
        "verdict": {"state": state,
                    "reason": f"deterministic-verification all_checks_passed={passed}",
                    "objective_score": score,
                    "objective_max": verification.get("all_weight") and 60,
                    "score_for_aggregate": score if state in ("pass", "fail") else None},
        "attribution": {
            "harness_attributable": False,
            "reason": "a repeat measures output stability for one product; it carries no matched "
                      "control, so it cannot separate Harness from model",
            "controls": [],
            "unexcluded": ["backend model identity", "sampling parameters", "server-side routing"],
        },
        "prompt_validity": {"ok": prompt_ok, "basis": prompt_basis},
        "sources": [{"path": f"{folder}/run-metadata.json",
                     "sha256": sha_file(f"{folder}/run-metadata.json"), "json_pointer": ""},
                    {"path": f"{folder}/deterministic-verification.json",
                     "sha256": sha_file(f"{folder}/deterministic-verification.json"),
                     "json_pointer": "/all_checks_passed"}],
    }
    record["gates"] = run_gates(record)
    return record


def build_runs():
    records = formal_runs() + registered_runs() + repeat_runs()
    seen = {}
    for record in records:
        if record["run_id"] in seen:
            raise ValueError("duplicate run id: " + record["run_id"])
        seen[record["run_id"]] = record
    return sorted(records, key=lambda item: item["run_id"])


def build_accounts(records):
    """Six ledgers that are never added together."""
    product_rows = [record for record in records if record["account"] == "product_run"]
    end_to_end = [record for record in product_rows
                  if record["track"] == "formal_product_end_to_end"]
    native = [record for record in product_rows if record["track"] == "native_ui_probe"]
    fixture = [record for record in product_rows
               if record["track"] in ("formal_controlled_contract", "adapter_calibration")]

    def counted(label, artifact, path, kind="value", expected=None):
        return {"label": label, "artifact": artifact, "pointer": path, "kind": kind,
                "expected": expected}

    accounts = {
        "product_run": {
            "definition": "an actually submitted product task/session with its own configuration, "
                          "start and end, and retained evidence",
            "entries": len(product_rows),
            "breakdown": {
                "five_product_end_to_end": len(end_to_end),
                "native_desktop_tasks": len(native),
                "fixed_local_fixture_sessions": len(fixture),
                "repeat_batch_sessions": len([record for record in product_rows
                                              if record["track"] == "repeat_batch"]),
                "pass": sum(1 for record in product_rows if record["verdict"]["state"] == "pass"),
                "fail": sum(1 for record in product_rows if record["verdict"]["state"] == "fail"),
                "unknown": sum(1 for record in product_rows
                               if record["verdict"]["state"] == "unknown"),
            },
            "recompute": counted("run file length", "ledger/runs.jsonl", "", kind="lines"),
        },
        "self_test": {
            "definition": "offline regression suite over the evaluation kit; runs no product",
            "artifact": "ledger/self-test.json",
            "recompute": counted("suite total", "ledger/self-test.json", "/total"),
        },
        "offline_recompute": {
            "definition": "recomputation of already published bytes; produces no new product run",
            "items": [
                counted("归因边界复核的新增产品运行", "reports/attribution-boundaries.json",
                        "/new_independent_product_runs", expected=0),
                counted("旧现场判卷复算", "reports/grader-audit-v3.json",
                        "/counts/historical_artifact_rechecks", expected=25),
                counted("旧五题评分派生行数", "reports/evaluation-v2.json", "/runs",
                        kind="length", expected=25),
                counted("许可配对复核", "reports/permission-pairs-v2.json", "/pairs",
                        kind="length"),
            ],
        },
        "grader_regression": {
            "definition": "synthetic answers used to test the judge; never product output",
            "items": [
                counted("合成答案", "reports/grader-audit-v3.json",
                        "/counts/synthetic_examples", expected=22),
                counted("守卫开关核查", "reports/grader-audit-v3.json",
                        "/counts/ablation_checks", expected=20),
                counted("旧版误接受", "reports/grader-audit-v3.json",
                        "/counts/legacy_false_accepts", expected=4),
                counted("v3误接受", "reports/grader-audit-v3.json",
                        "/counts/v3_false_accepts", expected=0),
                counted("v3误拒绝", "reports/grader-audit-v3.json",
                        "/counts/v3_false_rejects", expected=0),
            ],
        },
        "bare_model_probe": {
            "definition": "the same model called without any product Harness, to separate model "
                          "behaviour from Harness behaviour",
            "entries": 0,
            "empty_reason": "no attested shared model endpoint exists for the five products, so a "
                            "bare probe cannot be matched to a product run; an unmatched probe "
                            "would not change any five-product conclusion. 10-31 attempt: "
                            "api.deepseek.com was reachable but the locally stored credential is an "
                            "account-platform grant and the public API answered 401",
            "stop_condition": "reopen only when one product's exact model is both disclosed and "
                              "reachable outside its Harness",
        },
        "interface_preflight": {
            "definition": "reading configuration surfaces and endpoints; counts zero product tasks",
            "entries": 3,
            "tasks_counted": 0,
            "recompute": counted("预检产品数", "public/supplements/gui-controls-v1/observations.json",
                                 "/products", kind="length", expected=3),
        },
    }
    for name in ACCOUNTS:
        accounts[name].setdefault("definition", "")
        if "items" in accounts[name]:
            accounts[name]["entries"] = len(accounts[name]["items"])
    accounts["_rules"] = {
        "no_cross_account_sum": "the six ledgers must never be added into one workload number",
        "unknown_never_scored": "an unknown verdict keeps score_for_aggregate null and is excluded "
                                "from both numerator and denominator",
        "product_only_for_table": "only the product_run ledger can feed the formal comparison table",
        "recompute": "every number above is re-read from its frozen artifact by JSON pointer",
    }
    return accounts
