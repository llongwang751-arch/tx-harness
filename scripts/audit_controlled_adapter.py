"""Recompute the public controlled-adapter contract without running a product.

This verifies published consistency and the narrow fixture contract. A hashed
inventory or normalized event is not independent authentication of its observer.
Calibration attempts and admitted tasks are counted separately; neither a
configuration rejection nor an approval-blocked calibration is a product fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
MARKER = "CONTROLLED_TOOL_V1"
CALL_ID = "call_controlled_1"
MODEL = "fixed-tool-v1"
HEX = re.compile(r"[0-9a-f]{64}")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique)


def _jsonl(path):
    return [json.loads(line, object_pairs_hook=_unique)
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _local(folder, relative):
    if not isinstance(relative, str):
        raise ValueError("Non-string inventory path")
    name = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or name.is_absolute() or ".." in name.parts:
        raise ValueError("Unsafe inventory path: " + relative)
    path = folder / name
    if not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError("Inventory path escapes package: " + relative)
    for component in (path, *path.parents):
        if component == folder.parent:
            break
        if component.is_symlink():
            raise ValueError("Symlink in inventory path: " + relative)
    if not path.is_file():
        raise ValueError("Missing inventory file: " + relative)
    return path


def _manifest(folder):
    manifest = _load(folder / "manifest.json")
    if manifest.get("run_id", folder.name) != folder.name:
        raise ValueError("Manifest run identity differs from directory")
    rows = manifest.get("files", manifest.get("inventory"))
    if isinstance(rows, list):
        paths = [row.get("path", row.get("name")) for row in rows]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate inventory path")
        rows = dict(zip(paths, rows))
    if not isinstance(rows, dict) or not rows:
        raise ValueError("Manifest has no file inventory")
    actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*")
              if path.is_file() and path != folder / "manifest.json"}
    if set(rows) != actual:
        raise ValueError("Manifest inventory differs from package files")
    for name, spec in rows.items():
        path = _local(folder, name)
        if (not isinstance(spec, dict) or type(spec.get("bytes")) is not int
                or not isinstance(spec.get("sha256"), str) or not HEX.fullmatch(spec["sha256"])
                or path.stat().st_size != spec["bytes"] or _sha(path.read_bytes()) != spec["sha256"]):
            raise ValueError("Inventory hash or byte count differs: " + name)
    return manifest


def _markers(value):
    """Decode only an explicitly selected tool output, never arbitrary context."""
    if isinstance(value, dict):
        if value.get("marker") == MARKER:
            return [value]
        return [item for child in value.values() for item in _markers(child)]
    if isinstance(value, list):
        return [item for child in value for item in _markers(child)]
    if not isinstance(value, str):
        return []
    try:
        decoded = json.loads(value, object_pairs_hook=_unique)
    except ValueError:
        decoded = None
    if isinstance(decoded, (dict, list)):
        return _markers(decoded)
    found = []
    for match in re.finditer(r'\{\s*"marker"\s*:', value):
        try:
            decoded, _ = json.JSONDecoder(object_pairs_hook=_unique).raw_decode(value[match.start():])
        except ValueError:
            continue
        if isinstance(decoded, dict) and decoded.get("marker") == MARKER:
            found.append(decoded)
    return found


def _normal_terminal(rows, execution):
    terminals = [row for row in rows if row.get("kind") == "terminal"]
    return (bool(terminals) and execution.get("exit_code") == 0
            and all(row.get("normal") is True for row in terminals)
            and all(row.get("exit_code", 0) == 0 for row in terminals))


def audit_package(folder, fixture):
    """Return one transparent judgment; no private files or live calls are used."""
    folder = Path(folder)
    expected_data = fixture["arguments"]["text"].encode("utf-8")
    expected_sha = _sha(expected_data)
    result = {"run_id": folder.name, "phase": None, "product_id": None, "mode": None,
              "task_accepted": False, "independent_task_count": 0,
              "inventory_valid": False, "outcome": "unknown", "product_failure": False,
              "checks": {}, "missing_evidence": [], "integrity_errors": [],
              "is_error_observations": {}, "scope": "shared-tool dispatch/arguments/return contract only"}
    checks = result["checks"]

    def check(name, condition, evidence):
        checks[name] = {"passed": bool(condition), "evidence": evidence}

    try:
        _manifest(folder)
        result["inventory_valid"] = True
    except (OSError, ValueError, TypeError, KeyError) as error:
        result["integrity_errors"].append(str(error))
        return result
    objects = {}
    for name in ("execution.json", "launch.json", "model-events.jsonl", "mcp-events.jsonl", "native-events.jsonl"):
        path = folder / name
        if not path.is_file():
            result["missing_evidence"].append(name)
            continue
        try:
            objects[name] = _jsonl(path) if name.endswith(".jsonl") else _load(path)
        except (OSError, ValueError) as error:
            result["integrity_errors"].append(name + ": " + str(error))
    execution = objects.get("execution.json")
    if not isinstance(execution, dict):
        return result
    result.update({key: execution.get(key) for key in ("phase", "product_id", "mode")})
    result["task_accepted"] = execution.get("task_accepted") is True
    result["independent_task_count"] = int(result["task_accepted"])
    result["calibration_issue"] = execution.get("calibration_issue")
    check("run_identity", execution.get("run_id") == folder.name, ["execution.json"])
    check("registered_phase_and_mode", result["phase"] in {"calibration", "main"}
          and result["mode"] in {"success", "error"}, ["execution.json"])
    check("task_admitted", result["task_accepted"], ["execution.json", "native-events.jsonl"])
    if result["missing_evidence"] or result["integrity_errors"]:
        return result

    model = objects["model-events.jsonl"]
    mcp = objects["mcp-events.jsonl"]
    native = objects["native-events.jsonl"]
    launch = objects["launch.json"]
    if (not all(isinstance(row, dict) for rows in (model, mcp, native) for row in rows)
            or not isinstance(launch, dict)):
        result["integrity_errors"].append("Event rows and launch must be JSON objects")
        return result
    scene_path=folder/'reviewed-native-scene.jsonl'
    if scene_path.is_file():
        scene=_jsonl(scene_path)
        observed_admission=any(row.get('type')=='turn.started' or
            row.get('type')=='status' and row.get('phase')=='turn_start' for row in scene)
    else:
        observed_admission=False
    check('admission_matches_ordinary_scene', result['task_accepted']==observed_admission,
          ['execution.json','reviewed-native-scene.jsonl'])
    if result['task_accepted']!=observed_admission:
        result['integrity_errors'].append('Declared admission contradicts ordinary native scene')
        result['task_accepted']=observed_admission
        result['independent_task_count']=int(observed_admission)
    check('no_neural_model_inference',execution.get('real_model_inference') is False
          and execution.get('model_kind')=='deterministic_local_transport_fixture',['execution.json'])
    check('within_registered_budget',isinstance(execution.get('elapsed_seconds'),(int,float))
          and 0<execution['elapsed_seconds']<=execution.get('timeout_seconds',0)==120,['execution.json'])
    check("external_credentials_not_forwarded", launch.get("external_credentials_forwarded") is False,
          ["launch.json"])
    requests = [row for row in model if row.get("kind") == "model_request"]
    fixed = [row for row in model if row.get("kind") == "fixed_tool_request"]
    terminals = [row for row in model if row.get("kind") == "fixed_terminal"]
    tool_calls = [row for row in mcp if row.get("request", {}).get("method") == "tools/call"]
    check("two_model_requests", len(requests) == 2 and [row.get("sequence") for row in requests] == [1, 2]
          and execution.get("local_model_requests") == 2, ["model-events.jsonl", "execution.json"])
    check("model_identity", bool(requests) and all(row.get("model") == MODEL for row in requests),
          ["model-events.jsonl"])
    check("one_model_tool_dispatch", len(fixed) == 1 and fixed[0].get("sequence") == 1,
          ["model-events.jsonl"])
    check("fixed_arguments", len(fixed) == 1 and fixed[0].get("arguments") == fixture["arguments"]
          and fixed[0].get("arguments_sha256") == _sha(_encoded(fixture["arguments"])),
          ["model-events.jsonl", "fixture.json"])
    candidates = requests[0].get("tool_candidates", []) if requests else []
    canonical_target = None
    if len(candidates) == 1:
        candidate = candidates[0]
        canonical_target = ((candidate["namespace"] + "__") if candidate.get("namespace") else "") + candidate.get("name", "")
    check("one_exposed_target", len(candidates) == 1 and len(fixed) == 1
          and fixed[0].get("native_tool") == candidates[0]
          and canonical_target == "mcp__contract__probe_commit", ["model-events.jsonl"])
    check("one_mcp_call", len(tool_calls) == 1, ["mcp-events.jsonl"])
    mcp_payloads = []
    mcp_error_flag = None
    if len(tool_calls) == 1:
        call = tool_calls[0]
        params = call.get("request", {}).get("params", {})
        check("mcp_exact_arguments", params.get("name") == "probe_commit"
              and params.get("arguments") == fixture["arguments"], ["mcp-events.jsonl"])
        rpc_result = (call.get("response") or {}).get("result", {})
        mcp_payloads = _markers(rpc_result.get("content"))
        mcp_error_flag = rpc_result.get("isError")
    else:
        check("mcp_exact_arguments", False, ["mcp-events.jsonl"])
    expected_payload = ({"marker": MARKER, "mode": "success", "bytes": len(expected_data), "sha256": expected_sha}
                        if result["mode"] == "success" else
                        {"marker": MARKER, "mode": "error", "code": "E_FIXTURE_DENIED"})
    check("mcp_fixture_result", mcp_payloads == [expected_payload], ["mcp-events.jsonl", "fixture.json"])
    check("mcp_error_flag", mcp_error_flag is True if result["mode"] == "error"
          else mcp_error_flag in (False, None), ["mcp-events.jsonl"])

    returned = requests[1].get("tool_return_items", []) if len(requests) == 2 else []
    path = requests[1].get("path", "") if len(requests) == 2 else ""
    id_key, output_key = ("call_id", "output") if path.endswith("/responses") else ("tool_call_id", "content")
    correlated = [row for row in returned if row.get(id_key) == CALL_ID]
    actual_payloads = [payload for row in correlated for payload in _markers(row.get(output_key))]
    check("correlated_tool_return", len(returned) == 1 and len(correlated) == 1,
          ["model-events.jsonl"])
    check("model_received_actual_mcp_payload", actual_payloads == mcp_payloads == [expected_payload]
          and len(requests) == 2 and requests[1].get("fixture_return_payloads") == actual_payloads,
          ["model-events.jsonl", "mcp-events.jsonl"])
    check("fixed_terminal", len(terminals) == 1 and terminals[0].get("sequence") == 2
          and terminals[0].get("text") == fixture.get("terminal", "CONTROLLED_DONE"), ["model-events.jsonl"])
    check("no_fixture_transport_error", not any(row.get("kind") == "fixture_transport_error" for row in model),
          ["model-events.jsonl"])

    native_calls = [row for row in native if row.get("kind") == "tool_call"]
    native_returns = [row for row in native if row.get("kind") == "tool_result"]
    native_texts = [row.get("text") for row in native if row.get("kind") == "assistant_text"]
    tool_name = candidates[0].get("name") if len(candidates) == 1 else None
    direct_native_ids = (len(native_calls) == len(native_returns) == 1
                         and native_calls[0].get("call_id") == native_returns[0].get("call_id") == CALL_ID)
    item_native_ids = (result["product_id"] == "codex" and len(native_calls) == len(native_returns) == 1
                       and native_calls[0].get("call_id") is None and native_returns[0].get("call_id") is None
                       and isinstance(native_calls[0].get("native_item_id"), str)
                       and bool(native_calls[0]["native_item_id"])
                       and native_calls[0]["native_item_id"] == native_returns[0].get("native_item_id"))
    native_correlated = direct_native_ids or item_native_ids
    check("native_call_result_correlation", native_correlated, ["native-events.jsonl"])
    result["native_correlation"] = {
        "kind": "model_call_id_exposed" if direct_native_ids else "native_item_id_only" if item_native_ids else "unresolved",
        "model_call_id_verified_at_endpoint": bool(checks["correlated_tool_return"]["passed"]),
        "note": "A native item ID is not upgraded into an unexposed model call ID; unique frozen arguments and MCP/endpoint records provide additional correlation.",
    }
    check("native_exact_tool_call", len(native_calls) == 1 and native_correlated
          and native_calls[0].get("tool_name") == tool_name
          and native_calls[0].get("arguments") == fixture["arguments"], ["native-events.jsonl", "model-events.jsonl"])
    check("native_tool_result", len(native_returns) == 1 and native_correlated
          and native_returns[0].get("payload") == expected_payload, ["native-events.jsonl", "mcp-events.jsonl"])
    check("native_fixed_terminal_text", fixture.get("terminal", "CONTROLLED_DONE") in native_texts,
          ["native-events.jsonl"])
    check("native_normal_completion", _normal_terminal(native, execution), ["native-events.jsonl", "execution.json"])
    result["is_error_observations"] = {
        "mcp_is_error": mcp_error_flag,
        "mcp_source": "mcp-events.jsonl response.result.isError",
        "native_is_error": native_returns[0].get("is_error") if len(native_returns) == 1 else None,
        "native_source": native_returns[0].get("is_error_source", "not_exposed") if len(native_returns) == 1 else "missing",
        "native_status": native_returns[0].get("native_status") if len(native_returns) == 1 else None,
        "error_semantics_received": result["mode"] == "error" and actual_payloads == [expected_payload],
        "note": "Native boolean exposure is recorded separately from preserved synthetic error semantics.",
    }
    artifacts = sorted(path for path in folder.rglob("artifact.txt") if path.is_file())
    collected = sorted(path for path in (folder/'collected').rglob('*') if path.is_file())
    if result["mode"] == "success":
        check("artifact_exact_bytes", len(artifacts) == 1 and artifacts[0].read_bytes() == expected_data
              and collected==artifacts,
              [path.relative_to(folder).as_posix() for path in artifacts] + ["fixture.json"])
        declared = execution.get("artifact")
        check("artifact_receipt", isinstance(declared, dict) and declared.get("bytes") == len(expected_data)
              and declared.get("sha256") == expected_sha, ["execution.json"])
    else:
        check("error_mode_has_no_artifact", not artifacts and not collected and execution.get("artifact") is None,
              ["execution.json", "manifest.json"])
    passed = all(check["passed"] for check in checks.values())
    result["contract_satisfied"] = passed
    result["outcome"] = "pass" if passed else ("unknown" if result["phase"] == "calibration"
                                              or not result["task_accepted"] else "fail")
    result["product_failure"] = result["phase"] == "main" and result["outcome"] == "fail"
    result["failed_checks"] = [name for name, value in checks.items() if not value["passed"]]
    return result


def bind_registration(root,folder,result,fixture):
    """Bind every attempt to the immutable pre-execution commit, not today's runner."""
    execution=_load(folder/'execution.json')
    commit=execution.get('registration_commit','')
    name=execution.get('registration_file','')
    if not re.fullmatch(r'[0-9a-f]{7,40}',commit) or not re.fullmatch(r'(?:calibration(?:-r[234])?|protocol)\.json',name):
        raise ValueError('Invalid registration locator')
    def blob(path):return subprocess.check_output(['git','show',commit+':'+path],cwd=root,stderr=subprocess.PIPE)
    protocol_path='supplements/controlled-adapter-v1/'+name
    raw=blob(protocol_path);protocol=json.loads(raw,object_pairs_hook=_unique)
    if (root/protocol_path).read_bytes()!=raw:raise ValueError('Historical registration edited')
    spec=next((row for row in protocol['runs'] if row['run_id']==folder.name),None)
    if not spec or any(execution.get(key)!=spec.get(key) for key in ('product_id','mode')) or execution['phase']!=protocol['phase']:
        raise ValueError('Run identity/phase/mode not registered')
    for path,specification in protocol['files'].items():
        data=blob(path)
        if len(data)!=specification['bytes'] or _sha(data)!=specification['sha256']:
            raise ValueError('Registration source hash differs: '+path)
    expected_exe=protocol['executables'][execution['product_id']]
    if execution.get('executable_sha256')!=expected_exe['sha256']:
        raise ValueError('Executable not bound to registered build')
    if execution.get('version')!=protocol['installed_versions'][execution['product_id']]:
        raise ValueError('Version differs from registered installation')
    if execution.get('shared_tool_sha256')!=protocol['files']['scripts/controlled_probe_mcp.py']['sha256']:
        raise ValueError('Shared MCP source differs from registration')
    if execution.get('frozen_arguments_sha256')!=_sha(_encoded(fixture['arguments'])):
        raise ValueError('Frozen arguments receipt differs')
    if blob('supplements/controlled-adapter-v1/fixture.json')!=(root/'supplements/controlled-adapter-v1/fixture.json').read_bytes():
        raise ValueError('Shared fixture differs from registered bytes')
    timestamp=subprocess.check_output(['git','show','-s','--format=%cI',commit],cwd=root,text=True).strip()
    if datetime.fromisoformat(timestamp)>datetime.fromisoformat(execution['started_at']):
        raise ValueError('Registration commit after execution')
    result['registration']={'commit':commit,'path':protocol_path,'sha256':_sha(raw),
                            'committed_at':timestamp,'historical_source_blobs_verified':len(protocol['files'])}


def build(root=ROOT):
    root = Path(root)
    fixture_file = root / "supplements/controlled-adapter-v1/fixture.json"
    fixture = _load(fixture_file)
    if (not isinstance(fixture.get("arguments"), dict)
            or set(fixture["arguments"]) != {"text", "destination"}
            or not isinstance(fixture["arguments"]["text"], str)
            or fixture["arguments"]["destination"] != "artifact.txt"):
        raise ValueError("Unexpected frozen fixture arguments")
    base = root / "public/supplements/controlled-adapter-v1"
    packages = [audit_package(folder, fixture) for folder in sorted(base.glob("CA*")) if folder.is_dir()]
    for row in packages:
        try:bind_registration(root,base/row['run_id'],row,fixture)
        except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
            row['integrity_errors'].append('Registration: '+str(error))
            row['outcome']='unknown';row['product_failure']=False
        row['confidence']='high_for_public_record_consistency_and_frozen_contract_only'
        row['confidence_basis']='Pre-run commit blobs, actual endpoint and MCP records, native scene and original artifact hashes agree where checks pass; collection remains one AI-assisted operator, no external human review.'
    main=[row for row in packages if row['phase']=='main']
    protocol=_load(root/'supplements/controlled-adapter-v1/protocol.json')
    executions={row['run_id']:_load(base/row['run_id']/'execution.json') for row in packages}
    actual_order=sorted(main,key=lambda row:executions[row['run_id']]['started_at'])
    if [row['run_id'] for row in actual_order]!=[row['run_id'] for row in protocol['runs']]:
        raise ValueError('Main matrix or serial registered order differs')
    ordered=sorted(executions.values(),key=lambda row:row['started_at'])
    if any(datetime.fromisoformat(a['ended_at'])>datetime.fromisoformat(b['started_at'])
           for a,b in zip(ordered,ordered[1:])):
        raise ValueError('Recorded controlled product instances overlapped')
    groups={
        'C1':['task_admitted','one_model_tool_dispatch','fixed_arguments','one_exposed_target',
              'one_mcp_call','mcp_exact_arguments','native_exact_tool_call'],
        'C2':['mcp_fixture_result','mcp_error_flag'],
        'C3':['correlated_tool_return','model_received_actual_mcp_payload','native_tool_result'],
        'C4':['two_model_requests','fixed_terminal','no_fixture_transport_error',
              'native_fixed_terminal_text','native_normal_completion','within_registered_budget']}
    for row in packages:
        criteria={key:list(values) for key,values in groups.items()}
        criteria['C2']+=['artifact_exact_bytes','artifact_receipt'] if row['mode']=='success' else ['error_mode_has_no_artifact']
        row['metrics']={key:{'score':int(all(row['checks'].get(name,{}).get('passed') for name in names))
                if row['phase']=='main' and not row['integrity_errors'] else None,
                'checks':names,'rule':'supplements/controlled-adapter-v1/protocol.md',
                'confidence_basis':row['confidence_basis']} for key,names in criteria.items()}

    def counts(rows):
        admitted = [row for row in rows if row["task_accepted"]]
        return {"attempts": len(rows), "independent_tasks": len(admitted),
                "not_accepted_attempts": len(rows) - len(admitted),
                "passed_tasks": sum(row["outcome"] == "pass" for row in admitted),
                "failed_tasks": sum(row["product_failure"] for row in admitted),
                "unknown_tasks": sum(row["outcome"] == "unknown" for row in admitted),
                "contract_not_satisfied_calibration_tasks": sum(row["phase"] == "calibration"
                    and row.get("contract_satisfied") is False for row in admitted)}

    return {"schema": "controlled-adapter-public-audit/v1",
            "fixture": {"path": "supplements/controlled-adapter-v1/fixture.json",
                        "sha256": _sha(fixture_file.read_bytes()),
                        "arguments_sha256": _sha(_encoded(fixture["arguments"])),
                        "artifact_bytes": len(fixture["arguments"]["text"].encode("utf-8")),
                        "artifact_sha256": _sha(fixture["arguments"]["text"].encode("utf-8"))},
            "counts": {"all": counts(packages),
                       "calibration": counts([row for row in packages if row["phase"] == "calibration"]),
                       "main": counts([row for row in packages if row["phase"] == "main"])},
            "packages": packages,
            "limits": ["Only public recorded bytes and normalized events are recomputed; no private source is read.",
                       "Calibration outcomes are never counted as product failures.",
                       "Fixed local transport removes model sampling for this contract, not general model/Skill influence.",
                       "Trusted MCP write effects do not test product filesystem sandbox enforcement.",
                       "Hashes establish consistency rather than independent authentication of collection."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/controlled-adapter-v1.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build(args.root)
    output = args.output if args.output.is_absolute() else args.root / args.output
    if args.check:
        if not output.is_file() or _load(output) != report:
            raise SystemExit("Published controlled-adapter audit is absent or stale")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    errors = [row["run_id"] for row in report["packages"] if row["integrity_errors"]]
    print(json.dumps({"packages": len(report["packages"]), "counts": report["counts"],
                      "integrity_error_packages": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
