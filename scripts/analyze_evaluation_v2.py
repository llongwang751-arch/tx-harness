"""Read-only, deterministic diagnostics for the historical 25 selected episodes.

Only public evidence and frozen evaluator inputs are read. The old binary scores
are quoted, never replaced by a new field-level score. No product is launched.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from harness_eval import core  # noqa: E402

REVIEW = "reports/exploratory-score-review.json"
PRODUCTS = ("codex", "dsh", "workbuddy", "yuanbao", "doubao")
MISSING = object()
PRESERVATION_STATEMENT = "Original native download/export saved without content changes"


def pointer_part(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def child(pointer, value):
    return pointer + "/" + pointer_part(value)


def equal(actual, expected):
    return core.json_equal(actual, expected)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Sources:
    """Deny private/escaping paths even when a public record refers to them."""

    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.files = {}

    def path(self, relative):
        parts = Path(relative).parts
        if (Path(relative).is_absolute() or not parts
                or any(p.casefold() == "private" for p in parts)):
            raise ValueError("Only explicit public/evaluator relative paths are allowed")
        path = self.root.joinpath(relative)
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Source path escapes repository")
        if not (relative == REVIEW or relative.startswith(("public/pilots/", "cases/", "config/"))
                or relative == "harness_eval/core.py"):
            raise ValueError("Source is outside the public analysis allowlist: " + relative)
        for parent in (path, *path.parents):
            if parent == self.root:
                break
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise ValueError("Linked evidence is not allowed")
        return path

    def reference(self, relative, pointer="", locator=None):
        path = self.path(relative)
        if relative not in self.files:
            self.files[relative] = {
                "sha256": digest(path.read_bytes()) if path.is_file() else None,
                "present": path.is_file(),
            }
        result = {"path": relative, **self.files[relative], "json_pointer": pointer}
        if locator is not None:
            result["locator"] = locator
        return result

    def read_json(self, relative):
        self.reference(relative)
        return core.read_json(self.path(relative))


def difference(kind, actual, expected, actual_pointer="", expected_pointer="", **details):
    """Missing is represented explicitly; JSON null remains an observed null."""
    return {
        "kind": kind,
        "actual_present": actual is not MISSING,
        "actual": None if actual is MISSING else actual,
        "expected_present": expected is not MISSING,
        "expected": None if expected is MISSING else expected,
        "actual_pointer": actual_pointer,
        "expected_pointer": expected_pointer,
        **details,
    }


def json_differences(actual, expected, actual_pointer="", expected_pointer="", subset=False):
    """Compare JSON types/fields; preserve the frozen array ordering contract."""
    if equal(actual, expected):
        return []
    if isinstance(actual, dict) and isinstance(expected, dict):
        result = []
        keys = sorted(expected if subset else set(actual) | set(expected))
        for key in keys:
            av, ev = actual.get(key, MISSING), expected.get(key, MISSING)
            ap, ep = child(actual_pointer, key), child(expected_pointer, key)
            if av is MISSING or ev is MISSING:
                result.append(difference("missing_field" if av is MISSING else "extra_field",
                                         av, ev, ap, ep))
            else:
                result.extend(json_differences(av, ev, ap, ep))
        return result
    if isinstance(actual, list) and isinstance(expected, list):
        serialize = lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True)
        if Counter(map(serialize, actual)) == Counter(map(serialize, expected)):
            return [difference("array_order", actual, expected, actual_pointer, expected_pointer)]
        result = []
        for index in range(max(len(actual), len(expected))):
            av = actual[index] if index < len(actual) else MISSING
            ev = expected[index] if index < len(expected) else MISSING
            ap, ep = child(actual_pointer, index), child(expected_pointer, index)
            if av is MISSING or ev is MISSING:
                result.append(difference("missing_item" if av is MISSING else "extra_item",
                                         av, ev, ap, ep))
            else:
                result.extend(json_differences(av, ev, ap, ep))
        return result
    kind = "type_mismatch" if type(actual) is not type(expected) else "value_mismatch"
    return [difference(kind, actual, expected, actual_pointer, expected_pointer)]


def csv_differences(path, keys, expected, expected_pointer):
    """Index by the frozen CSV primary key, without silently deduplicating rows."""
    columns = list(expected[0])
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        headers, rows = reader.fieldnames, list(reader)
    if (not headers or len(headers) != len(set(headers)) or set(headers) != set(columns)):
        return [difference("csv_columns", headers, columns, locator={"csv_header": True})]
    invalid = [i for i, row in enumerate(rows) if set(row) != set(columns)
               or any(v is None for v in row.values())]
    if invalid:
        return [difference("csv_row_shape", rows[i], columns,
                           locator={"csv_data_row": i + 1}) for i in invalid]
    actual_index = defaultdict(list)
    expected_index = {}
    for index, row in enumerate(rows):
        actual_index[tuple(row[k] for k in keys)].append((index, row))
    for index, row in enumerate(expected):
        pk = tuple(row[k] for k in keys)
        if pk in expected_index:
            raise ValueError("Duplicate oracle CSV primary key")
        expected_index[pk] = (index, row)
    result = []
    for pk in sorted(set(actual_index) | set(expected_index)):
        found, wanted = actual_index.get(pk, []), expected_index.get(pk)
        locator = {"primary_key": dict(zip(keys, pk))}
        if len(found) > 1:
            result.append(difference("duplicate_primary_key", [row for _, row in found],
                                     wanted[1] if wanted else MISSING,
                                     expected_pointer=child(expected_pointer, wanted[0]) if wanted else "",
                                     locator={**locator, "csv_data_rows": [i + 1 for i, _ in found]}))
            continue
        if not found:
            result.append(difference("missing_row", MISSING, wanted[1],
                                     expected_pointer=child(expected_pointer, wanted[0]), locator=locator))
        elif not wanted:
            result.append(difference("extra_row", found[0][1], MISSING,
                                     locator={**locator, "csv_data_row": found[0][0] + 1}))
        else:
            ai, av = found[0]
            ei, ev = wanted
            for column in columns:
                if av[column] != ev[column]:
                    result.append(difference("csv_value", av[column], ev[column],
                                             expected_pointer=child(child(expected_pointer, ei), column),
                                             locator={**locator, "csv_data_row": ai + 1, "column": column}))
    return result


def classification(case_id, check_id):
    number = int(check_id.rsplit("C", 1)[1])
    if case_id == "T01":
        return "业务结果及异常识别"
    if case_id == "T02":
        return ("业务裁决结果" if number <= 3 else "规则引文内容" if number == 4
                else "冲突处置及版本选择声明")
    if case_id == "T03":
        return "文件内容及字节约束" if number <= 4 else "修改及未修改声明"
    if case_id == "T04":
        return "业务换算结果" if number <= 4 else "缺失及恢复声明"
    return ("业务账单结果" if number <= 3 else "来源审计及边界声明" if number <= 7
            else "汇总文件禁词检查")


def diagnose_check(sources, base, case_id, check, oracle):
    cfg, kind = check["config"], check["kind"]
    actual_name = base + "/outputs/" + cfg["path"]
    actual_path = sources.path(actual_name)
    expected_name = "cases/" + case_id + "/oracle.json"
    ep = child("", cfg["oracle_key"]) if "oracle_key" in cfg else ""
    expected = oracle.get(cfg.get("oracle_key"), MISSING)
    if kind == "bytes_equal":
        expected_name = "cases/" + case_id + "/" + cfg["reference"]
    if kind in ("text_contains", "text_excludes", "file_exists"):
        expected_name = "cases/" + case_id + "/case.json"
        case = sources.read_json(expected_name)
        ci = next(i for i, c in enumerate(case["checks"]) if c["id"] == check["id"])
        ep = f"/checks/{ci}/config"
    ar, er = sources.reference(actual_name), sources.reference(expected_name, ep)
    status, differences = "compared", []
    try:
        if not actual_path.is_file():
            status = "missing_file"
            case_name = f"cases/{case_id}/case.json"
            case = sources.read_json(case_name)
            ci = next(i for i, c in enumerate(case["checks"]) if c["id"] == check["id"])
            differences = [difference("missing_file", MISSING, cfg["path"],
                                      expected_pointer=f"/checks/{ci}/config/path",
                                      expected_source_path=case_name)]
        elif kind in ("exact_json", "json_fields"):
            actual = sources.read_json(actual_name)
            differences = json_differences(actual, expected, expected_pointer=ep,
                                            subset=kind == "json_fields")
        elif kind == "csv_rows":
            differences = csv_differences(actual_path, cfg["key_columns"], expected, ep)
        elif kind == "bytes_equal":
            av, ev = actual_path.read_bytes(), sources.path(expected_name).read_bytes()
            if av != ev:
                index = next((i for i, (a, e) in enumerate(zip(av, ev)) if a != e), min(len(av), len(ev)))
                differences = [difference("bytes_mismatch", {"bytes": len(av), "sha256": digest(av)},
                                          {"bytes": len(ev), "sha256": digest(ev)},
                                          locator={"first_different_byte_offset": index})]
        elif kind in ("text_contains", "text_excludes"):
            content = actual_path.read_text(encoding="utf-8-sig")
            for i, value in enumerate(cfg["values"]):
                present = value in content
                if present != (kind == "text_contains"):
                    differences.append(difference("text_constraint", {"text": value, "present": present},
                                                  {"text": value, "present": kind == "text_contains"},
                                                  expected_pointer=ep + f"/values/{i}"))
        elif kind != "file_exists":
            raise ValueError("Unsupported frozen check kind: " + kind)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, csv.Error) as exc:
        status = "parse_error"
        # Do not report an invented field value when parsing was impossible.
        differences = [difference("parse_error", MISSING, {"format": kind},
                                  expected_pointer=ep, error=str(exc))]
    for item in differences:
        item["actual_source"] = sources.reference(actual_name, item.pop("actual_pointer"), item.get("locator"))
        item["expected_source"] = sources.reference(item.pop("expected_source_path", expected_name), item.pop("expected_pointer"))
    return {"id": check["id"], "title": check["title"], "kind": kind, "path": cfg["path"],
            "classification": classification(case_id, check["id"]),
            "status": status, "matches_frozen_contract": not differences,
            "actual_source": ar, "expected_source": er, "differences": differences,
            "confidence": "high_for_compared_bytes_only", "attribution": "unresolved"}


def instant(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timing evidence must include timezone")
    return parsed


def elapsed(value, start):
    return round((instant(value) - instant(start)).total_seconds(), 6) if value and start else None


def observed_value(sources, path, data, field, start=None, pointer_prefix=""):
    return {"value": data.get(field), "seconds_after_submit": elapsed(data.get(field), start),
            "source": sources.reference(path, child(pointer_prefix, field) if field in data else pointer_prefix,
                                        None if field in data else {"missing_json_field": field}),
            "observed": field in data}


def preserved_receipt(sources, base, artifact, output, start, receipt_path, ai, oi):
    """A late observation is unknown, never retrospective evidence of failure."""
    ap, op = f"/artifacts/{ai}", f"/artifacts/{ai}/outputs/{oi}"
    fields = ["downloaded_at", "download_available_observed_at", "first_existence_observed_at", "save_action_at"]
    times = {field: observed_value(sources, receipt_path, artifact, field, start, ap) for field in fields}
    native_name = base + "/" + artifact["public_native_file"]
    logical_name = base + "/outputs/" + output["logical_path"]
    nr, lr = sources.reference(native_name), sources.reference(logical_name)
    hash_matches = (nr["present"] and lr["present"] and nr["sha256"] == artifact.get("sha256")
                    and lr["sha256"] == output.get("sha256") == nr["sha256"]
                    and output.get("zip_member") is None)
    # This is an operator public provenance statement, not independent attestation.
    retained = artifact.get("source_projection") == PRESERVATION_STATEMENT
    observations = [times[f]["seconds_after_submit"] for f in fields[:3]
                    if times[f]["seconds_after_submit"] is not None]
    before = bool(observations) and 0 <= min(observations) <= 1200
    supported = bool(hash_matches and retained and before)
    return {"logical_path": output["logical_path"], "times": times,
            "preservation_statement": artifact.get("source_projection"),
            "preservation_source": sources.reference(receipt_path, ap + "/source_projection"),
            "native_source": nr, "logical_source": lr,
            "recorded_hash_sources": [sources.reference(receipt_path, ap + "/sha256"),
                                      sources.reference(receipt_path, op + "/sha256")],
            "current_hashes_match_retained_original": bool(hash_matches),
            "pre_cutoff_retained_bytes_supported": supported,
            "confidence": "medium_operator_public_provenance" if supported else "unknown",
            "reason": ("前截止本地原件观察、原件保留声明及当前两份字节哈希一致；限公共采集投影，非独立签名证明。"
                       if supported else "无完整前截止原件字节链；保存动作、晚观察或最终哈希不倒推截止结果。")}


def timeline(sources, run, metadata_path, metadata, required, historical_score):
    start = metadata.get("started_at")
    terminal = None
    if metadata.get("parent_turn_ends"):
        index = len(metadata["parent_turn_ends"]) - 1
        item = metadata["parent_turn_ends"][index]
        terminal = {"value": item.get("received_at"), "seconds_after_submit": elapsed(item.get("received_at"), start),
                    "source": sources.reference(metadata_path, f"/parent_turn_ends/{index}/received_at"),
                    "basis": "同父会话普通 turn/end 观察；不等于文件取得或截止快照。"}
    else:
        field = next((f for f in ("completion_observed_at", "native_ended_at", "ended_at", "finished_at")
                      if metadata.get(f)), None)
        if field:
            terminal = {**observed_value(sources, metadata_path, metadata, field, start),
                        "basis": metadata.get("completion_basis", metadata.get("timing_basis", "采集元数据终态；精确服务完成时间未知。"))}
    delivery_review = None
    # This public metadata explicitly distinguishes an earlier ordinary reply
    # from its final delivery review. Do not substitute that later review time.
    for i, note in enumerate(metadata.get("retrieval_limitations", [])):
        match = re.search(r"Ordinary final text first observed at ([0-9:.]+Z) \(([0-9.]+) seconds\)", note)
        if match and start:
            value = start[:10] + "T" + match[1]
            if abs(elapsed(value, start) - float(match[2])) > .000001:
                raise ValueError("Public prose timestamp and elapsed seconds disagree")
            delivery_review = terminal
            terminal = {"value": value, "seconds_after_submit": elapsed(value, start),
                        "source": sources.reference(metadata_path, f"/retrieval_limitations/{i}"),
                        "basis": "公共元数据报告的首次普通终态正文时间；该早期capture未选入公共UI切片，非精确服务完成时间。",
                        "confidence": "medium_operator_report"}
    base = run["base"]
    receipt_path = base + "/download-receipts.json"
    evidence = []
    receipt_exists = sources.path(receipt_path).is_file()
    if receipt_exists:
        receipts = sources.read_json(receipt_path)
        for ai, artifact in enumerate(receipts.get("artifacts", [])):
            for oi, output in enumerate(artifact.get("outputs", [])):
                evidence.append(preserved_receipt(sources, base, artifact, output, start, receipt_path, ai, oi))
    covered = {entry["logical_path"] for entry in evidence if entry["pre_cutoff_retained_bytes_supported"]}
    all_supported = bool(required) and set(required) <= covered
    return {
        "submit": observed_value(sources, metadata_path, metadata, "started_at"),
        "submit_basis": metadata.get("start_basis", "原生采集提交时间；SDK入队回执不等于完成，CLI启动也不等于服务接收。"),
        "ordinary_terminal_observation": terminal,
        "later_delivery_review_observation": delivery_review,
        "artifact_acquisition": evidence,
        "artifact_acquisition_time_status": "per_file_public_receipts" if receipt_exists else "unknown_no_timestamped_original_receipt",
        "budget_seconds": 1200,
        "cutoff_at": (instant(start) + timedelta(seconds=1200)).isoformat() if start else None,
        "cutoff_evidence_status": "unknown_no_independent_cutoff_snapshot",
        "strict_cutoff_score": None,
        "within_budget_obtained_originals": {
            "evidence_status": "supported_by_public_retained_original_chain" if all_supported else "unknown",
            "historical_binary_score_for_obtained_originals": historical_score if all_supported else None,
            "confidence": "medium_operator_public_provenance" if all_supported else "unknown",
            "limitation": "只支持预算内已取得并保留的这些原件可复核；不证明后台未再改写或第1200秒的完整状态。",
        },
        "final_available_artifact_score_historical": historical_score,
        "required_paths_without_pre_cutoff_byte_chain": sorted(set(required) - covered),
        "recorded_observation_flags": {key: {"value": metadata[key], "source": sources.reference(metadata_path, "/" + key)}
                                       for key in ("budget_observation_valid", "collector_outage", "timed_out") if key in metadata},
        "confidence": "unknown_for_strict_cutoff",
        "limitation": "普通终态或最终评分不证明1200秒时的字节；前截止保留原件链只支持对应文件结果，不证明远端截止状态/精确下载时刻。"
    }


def review_evidence(sources, run, review_index, dimensions):
    """Keep concrete public locators, plus a pointer to their historical review row."""
    result = []
    for mi, manual in enumerate(run.get("manual", [])):
        if manual["dimension"] not in dimensions:
            continue
        for ei, evidence in enumerate(manual.get("evidence", [])):
            path = evidence["source_path"]
            if not path.startswith("public/pilots/"):
                continue
            result.append({"review_reference": sources.reference(REVIEW, f"/runs/{review_index}/manual/{mi}/evidence/{ei}"),
                           "source": sources.reference(path, locator=evidence.get("locator")),
                           "historical_source_sha256": evidence.get("source_sha256"),
                           "current_hash_matches_historical_reference": sources.reference(path)["sha256"] == evidence.get("source_sha256")})
    return result


def recovery(sources, run, ri, metadata_path, metadata):
    if run["case_id"] != "T04":
        return None
    product, base = run["product_id"], run["base"]
    references = review_evidence(sources, run, ri, {"process", "interaction"})
    if product == "codex":
        fields = ("request_or_candidate_seconds_after_start", "release_mode_recorded", "released_file",
                  "actual_resume_stdin_seconds_after_start", "exact_session_match", "adapter_effect")
        note = "主动请求后由适配器中止并以同一 session resume；同会话续接成立，桌面原生恢复未测。"
        status = "active_request_adapter_same_session_resume"
    elif product == "dsh":
        fields = ("request_seconds_after_submission", "supplement_prompt_receipt", "session_id", "parent_turn_ends", "release_protocol_deviation")
        note = "主动请求后同一SDK会话补发并观察后续终态；语义复核延迟18.052秒，非零延迟正式计时。"
        status = "active_request_sdk_continuation"
    elif product == "workbuddy":
        fields = ("release", "completion_observed_at")
        status = "active_request_visible_task_continuation"
        note = "主动请求后将原rates文件置入任务工作区，发送固定回复并继续同一可见任务；内部会话及执行边界未知。"
    else:
        fields = ("release", "completion_observed_at")
        status = "active_request_visible_task_continuation"
        note = ("主动请求、原生附件补发并继续同一可见任务；内部会话及执行边界未知。"
                if product != "doubao" else "33.201秒观察到主动请求；固定补发经原生询问弹层提交一次并续接，同一可见任务；内部会话未知。")
    facts = {field: {"value": metadata[field], "source": sources.reference(metadata_path, "/" + field)}
             for field in fields if field in metadata}
    release_path = base + "/release.json"
    if sources.path(release_path).is_file():
        release = sources.read_json(release_path)
        facts["release_record"] = {"value": release, "source": sources.reference(release_path)}
    return {"status": status, "note": note, "facts": facts, "references": references,
            "confidence": "medium_for_public_observed_continuity", "unknown": "远端内部线程、完整执行过程及唯一恢复责任",
            "attribution": "unresolved_end_to_end_configuration"}


def common_e2(sources, run, ri, metadata_path, metadata, case, diagnostics):
    present = sorted({check["path"] for check in diagnostics if check["actual_source"]["present"]})
    absent = sorted(set(case["required_outputs"]) - set(present))
    if absent:
        structure, note = "not_obtained_at_recorded_review", "指定交付位置未取得所需原件；远端内部是否生成未知。"
    elif run["case_id"] == "T03" and run["product_id"] == "doubao":
        structure, note = "flat_native_cards_with_logical_bundle_mapping", "五张平铺原件卡片；评测员按逻辑路径重组bundle，未证明原生交付目录结构。"
    elif run["case_id"] == "T03":
        structure, note = "required_bundle_paths_in_recorded_workspace", "公共原生文件/工作区路径及交付引用支持bundle路径；内容正确性另查。"
    else:
        structure, note = "required_flat_artifacts_available", "所需平铺原件可取得；传输/存储映射见逐文件来源。"
    fields = ("collected_outputs", "outputs", "product_deliverables", "native_originals", "retrieval_limitations")
    return {"run_id": run["run_id"], "case_id": run["case_id"],
            "real_files_obtainable": {"status": "all_required_obtained" if not absent else "missing_at_recorded_review",
                                      "present_paths": present, "missing_paths": absent,
                                      "confidence": "high_for_published_local_bytes",
                                      "sources": [check["actual_source"] for check in diagnostics
                                                  if check["path"] in case["required_outputs"]]},
            "native_delivery_structure": {"status": structure, "note": note,
                                          "confidence": "medium_public_provenance", "unknown": "远端完整原生目录/未采集交付入口",
                                          "metadata_sources": [sources.reference(metadata_path, "/" + f) for f in fields if f in metadata]},
            "t04_request_release_continuation": recovery(sources, run, ri, metadata_path, metadata),
            "review_public_references": review_evidence(sources, run, ri, {"delivery"}),
            "attribution": "unresolved_end_to_end_configuration"}


def extra_e1(sources, run, ri, metadata_path, metadata):
    public = review_evidence(sources, run, ri, {"process", "boundary"})
    event_paths = sorted({ref["source"]["path"] for ref in public
                          if ref["source"]["path"].endswith(".jsonl")})
    native_types = set()
    for ref in public:
        locator = ref["source"].get("locator", {})
        if locator.get("native_event_type"):
            native_types.add(locator["native_event_type"])
    detailed = bool(native_types & {"command_execution", "tool_call", "tool_result"})
    return {"run_id": run["run_id"],
            "status": "additional_public_native_execution_projection" if detailed else "ordinary_ui_projection_internal_execution_unknown",
            "public_event_paths": event_paths, "referenced_native_event_types": sorted(native_types),
            "references": public,
            "metadata_sources": [sources.reference(metadata_path, "/" + f) for f in
                                 ("actual_tool_calls", "os_sandbox_verified", "network_absence_independently_verified", "limitations") if f in metadata],
            "confidence": "medium_for_cited_projection_only",
            "unknown": "未公开调用、实际完整参数、系统/网络访问及隐藏过程",
            "attribution": "unresolved", "score": None,
            "interpretation": "E1只增加可审计范围；GUI未公开工具流保持未知，不因CLI日志丰富扣GUI分。"}


def numeric_delta(item):
    if not item["actual_present"] or not item["expected_present"]:
        return None
    a, e = item["actual"], item["expected"]
    if isinstance(a, bool) or isinstance(e, bool):
        return None
    try:
        return int(a) - int(e)
    except (TypeError, ValueError):
        return None


def propagation(diagnostics):
    """Show co-occurrence and arithmetic links, without inferring one root cause."""
    ledger, summaries = [], []
    for check in diagnostics:
        for di, item in enumerate(check["differences"]):
            if item["kind"] not in {"csv_value", "value_mismatch", "type_mismatch"}:
                continue
            field = item.get("locator", {}).get("column", item["actual_source"]["json_pointer"].rsplit("/", 1)[-1])
            if not field.endswith("_cents"):
                continue
            delta = numeric_delta(item)
            if delta is None:
                continue
            entry = {"check_id": check["id"], "difference_index": di, "path": check["path"],
                     "field": field, "actual": item["actual"], "expected": item["expected"],
                     "delta_actual_minus_expected": delta,
                     "primary_key": item.get("locator", {}).get("primary_key"),
                     "actual_source": item["actual_source"], "expected_source": item["expected_source"]}
            (ledger if check["kind"] == "csv_rows" else summaries).append(entry)
    if not ledger and not summaries:
        return None
    sums = defaultdict(int)
    for item in ledger:
        sums[item["field"]] += item["delta_actual_minus_expected"]
    links = [{"field": item["field"], "ledger_field_delta_sum": sums[item["field"]],
              "summary_delta": item["delta_actual_minus_expected"],
              "arithmetic_equal": sums[item["field"]] == item["delta_actual_minus_expected"]}
             for item in summaries if item["field"] in sums]
    return {"ledger_differences": ledger, "summary_differences": summaries,
            "same_named_field_delta_links": links,
            "interpretation": ("台账与汇总均有差异；对应差额仅描述传播相容性，差额不同也原样展示。"
                               if ledger and summaries else "当前只在所列层面发现数值差异；未把未见差异的汇总补成错误。"),
            "causal_root": "unknown", "limitation": "多个字段/检查可能依赖同一计算，也可能独立出错；差异数不是独立失败数或新能力分。"}


def analyze_run(sources, run, ri):
    case_id, base = run["case_id"], run["base"]
    case = sources.read_json(f"cases/{case_id}/case.json")
    oracle = sources.read_json(f"cases/{case_id}/oracle.json")
    metadata_path = next(base + "/" + name for name in ("metadata.json", "run-metadata.json")
                         if sources.path(base + "/" + name).is_file())
    metadata = sources.read_json(metadata_path)
    verification_path = run["objective"]["source_path"]
    historical_verification = sources.read_json(verification_path)
    old_checks = {c["id"]: (i, c) for i, c in enumerate(historical_verification["checks"])}
    diagnostics, classifications = [], {}
    for ci, check in enumerate(case["checks"]):
        result = diagnose_check(sources, base, case_id, check, oracle)
        oi, old = old_checks[check["id"]]
        result["frozen_check_source"] = sources.reference(f"cases/{case_id}/case.json", f"/checks/{ci}")
        result["historical_binary"] = {"passed": old["passed"], "weight_of_100": check["weight"],
                                       "points_of_60": round(check["weight"] * .6 if old["passed"] else 0, 4),
                                       "source": sources.reference(verification_path, f"/checks/{oi}")}
        result["historical_binary_matches_recomparison"] = old["passed"] == result["matches_frozen_contract"]
        bucket = classifications.setdefault(result["classification"], {"maximum_in_old_60": 0, "earned_in_old_60": 0, "check_ids": []})
        bucket["maximum_in_old_60"] = round(bucket["maximum_in_old_60"] + check["weight"] * .6, 4)
        bucket["earned_in_old_60"] = round(bucket["earned_in_old_60"] + result["historical_binary"]["points_of_60"], 4)
        bucket["check_ids"].append(check["id"])
        diagnostics.append(result)
    old_score = run["objective"]["score"]
    recomputed = round(sum(c["historical_binary"]["weight_of_100"] * .6 for c in diagnostics if c["matches_frozen_contract"]), 4)
    missing = sorted({c["path"] for c in diagnostics if c["status"] == "missing_file"})
    differences = [d for c in diagnostics for d in c["differences"]]
    return {"run_id": run["run_id"], "product_id": run["product_id"], "case_id": case_id,
            "source_review": sources.reference(REVIEW, f"/runs/{ri}"), "metadata_source": sources.reference(metadata_path),
            "historical_objective": {"score": old_score, "maximum": 60,
                                     "source": sources.reference(REVIEW, f"/runs/{ri}/objective"),
                                     "verification_source": sources.reference(verification_path),
                                     "current_verification_hash_matches_review": sources.reference(verification_path)["sha256"] == run["objective"]["source_sha256"],
                                     "binary_recomparison_consistent": recomputed == old_score and all(c["historical_binary_matches_recomparison"] for c in diagnostics)},
            "error_counts_without_new_denominator": {"observed_value_or_structure_differences": sum(d["kind"] not in {"missing_file", "parse_error"} for d in differences),
                                                    "missing_files": len(missing), "missing_paths": missing,
                                                    "parse_failed_checks": sum(c["status"] == "parse_error" for c in diagnostics)},
            "check_classification_old_weight_only": classifications,
            "checks": diagnostics, "cross_artifact_error_links": propagation(diagnostics),
            "timeline": timeline(sources, run, metadata_path, metadata, case["required_outputs"], old_score),
            "common_e2": common_e2(sources, run, ri, metadata_path, metadata, case, diagnostics),
            "additional_e1_audit": extra_e1(sources, run, ri, metadata_path, metadata),
            "new_capability_score": None}


def build_report(root=ROOT):
    sources = Sources(root)
    review = sources.read_json(REVIEW)
    extra_ids = set(review["additional_product_failure_episode_ids"])
    selected = [(i, run) for i, run in enumerate(review["runs"]) if run["run_id"] not in extra_ids]
    if (len(selected) != 25 or len({(r["product_id"], r["case_id"]) for _, r in selected}) != 25
            or {r["product_id"] for _, r in selected} != set(PRODUCTS)):
        raise ValueError("Historical selected scope is not the expected 5 x 5; refuse silent reselection")
    sources.reference("harness_eval/core.py")
    sources.reference("config/protocol.json")
    sources.reference("config/rubric.json")
    rows = [analyze_run(sources, run, i) for i, run in selected]
    e2 = [{"product_id": product, "cases": [row["common_e2"] for row in rows if row["product_id"] == product],
           "confidence": "per_case_separate", "attribution": "unresolved", "score": None} for product in PRODUCTS]
    result = {
        "schema": "tx-harness/evaluation-v2/v1", "generated_at": None,
        "generation_basis": "确定性离线派生；不读取系统时钟、不读取private、不启动产品、不修改旧原件及评分。",
        "scope": {"selected_episode_count": 25, "products": list(PRODUCTS), "cases": [f"T0{i}" for i in range(1, 6)],
                  "selection_source": sources.reference(REVIEW, "/runs"),
                  "historical_review_episode_count": len(review["runs"]),
                  "additional_failure_ids_excluded_from_selected_matrix": sorted(extra_ids),
                  "additional_failure_source": sources.reference(REVIEW, "/additional_product_failure_episode_ids"),
                  "note": "沿用旧25组合，额外豆包本地失败仍保留原审阅，不换入矩阵；31原包不重选。"},
        "method": [
            "逐个冻结检查比对最终取得原件；CSV按主键，JSON逐字段且区分布尔/数值、缺失/null，数组保留冻结顺序。所有差异列实际/期望及来源。",
            "旧binary整块检查和60分原值只引用、复算一致性；字段诊断不生成新能力分，不以缺失文件补零值。",
            "T04 incident的18/60、T05 source_audit的21/60属于文件声明；声明正确不等于请求恢复、无外传或执行约束真实成立。",
            "1200秒严格截止分须有独立保留的截止快照或结束停止后的当时全量字节；本次均缺证，strict_cutoff_score保持null。completed、普通正文、卡片、最终哈希、mtime不倒推截止字节。",
            "另列预算内取得原件的留存链支持：前截止存在观察、公共未改内容声明和两份原件哈希相符，置信medium且依赖Operator；只描述这些当时原件，不证明后台未再改写。晚观察不直接判截止失败。",
            "E2共同矩阵只描述可取得文件、原生结构和T04续接。E1执行审计另列，不把CLI的日志丰富换成GUI低分。",
            "跨台账/汇总差额描述相关错误和传播相容性；未鉴定唯一根因，差异数不等于独立错误数。",
        ],
        "runs": rows, "common_e2_matrix": e2,
        "additional_e1_audit": [row["additional_e1_audit"] for row in rows],
        "historical_auxiliary_only": {"aggregates_unchanged": review["aggregates"],
                                      "source": sources.reference(REVIEW, "/aggregates"),
                                      "interpretation": "旧缺证均值/综合算术范围只作历史辅助；范围为未知维度0到满权重填充，非置信区间，也不包含已评分项评审误差。",
                                      "weight_sensitivity": "整块权重使单个台账字段错误可能失去18/60或21/60，并与汇总重复受罚；声明块又占T04的18/60、T05的21/60。换权重或拆块可能改变综合值和相对顺序。此版仅列错误数与分类，不选新权重、不造共同字段分母。"},
        "limitations": [
            "后验选定的五产品五题单次入口记录，另有额外失败和先前调试；不是随机抽样或预注册主实验，不估计一般成功率、显著性或冠军。",
            "产品模型、Skill、权限、SDK/桌面入口和环境未匹配；观察仅支持相应端到端配置，非纯Harness因果比较。",
            "缺证及观察中断不是零能力；最终原件分与严格截止证据分开，未知项不补分、不用于等预算排名。",
            "公开来源本身来自同一Operator/agent采集及审阅；哈希证明版本一致，不能证明真实性、完整性或完整无越界。",
            "声明文件和文件禁词检查只证明对应最终文本；不能证明全过程未修改输入、未访问网络、未外传。",
        ],
    }
    result["sources"] = {path: sources.files[path] for path in sorted(sources.files)}
    return result


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def markdown(report):
    lines = ["# 评测派生复核 v2", "",
             "沿用旧25个选定组合，仅新增诊断。旧原包、整块分及历史综合值均保留；不产生新能力总分或排名。完整逐字段差异、SHA-256与JSON Pointer见 [JSON](evaluation-v2.json)。", "",
             "## 原件结果与1200秒证据", "",
             "普通终态、原件取得和截止字节分别记录。`unknown`不是零分或超时失败。预算内原件留存链的支持依赖公共Operator投影，只支持这些已取得原件；不证明后台未再改写或第1200秒状态。全部严格截止分保持null，CLI/SDK/WB的最终inventory或completed不足以证明截止字节。", "",
             "| 选定现场 | 旧最终原件分 /60 | 字段/结构差异 | 缺文件 | 解析失败检查 | 普通终态观察秒 | 最晚原件观察秒 | 预算内取得原件留存链 | 严格截止证据 |", "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for row in report["runs"]:
        counts, time = row["error_counts_without_new_denominator"], row["timeline"]
        terminal = time["ordinary_terminal_observation"]
        te = terminal["seconds_after_submit"] if terminal else None
        observed = [entry["times"][field]["seconds_after_submit"] for entry in time["artifact_acquisition"]
                    for field in ("downloaded_at", "download_available_observed_at", "first_existence_observed_at")
                    if entry["times"][field]["seconds_after_submit"] is not None]
        state = ("有支持（中等置信）" if time["within_budget_obtained_originals"]["evidence_status"] != "unknown" else "unknown")
        lines.append(f"| {row['run_id']} | {row['historical_objective']['score']:g} | {counts['observed_value_or_structure_differences']} | {counts['missing_files']} | {counts['parse_failed_checks']} | {te if te is not None else 'unknown'} | {max(observed) if observed else 'unknown'} | {state} | unknown |")
    consistent = all(row["historical_objective"]["binary_recomparison_consistent"] for row in report["runs"])
    supported = sum(row["timeline"]["within_budget_obtained_originals"]["evidence_status"] != "unknown" for row in report["runs"])
    lines += ["", f"25现场旧binary与当前字节重比对{'全部一致' if consistent else '存在差异，见JSON'}。{supported}现场有预算内已取得原件的留存链支持，可复核对应当时原件分；其余{25-supported}现场该链未知。全部25现场严格第1200秒结果均未知；晚取得、保存点击及普通卡片不倒推早期字节。元宝T03普通终态正文报告42.204秒、最后交付复查150.272秒，二者分开。", "",
              "时间与文件来源按每行JSON的 `metadata_source`、`timeline.*.source`、`checks[].actual_source/expected_source` 定位；每个引用带完整路径、SHA-256及JSON Pointer或CSV主键。", "",
              "## 具体差异", ""]
    for row in report["runs"]:
        failed = [check for check in row["checks"] if check["differences"]]
        if not failed:
            continue
        lines += [f"### {row['run_id']}", ""]
        for check in failed:
            for diff in check["differences"]:
                loc = diff.get("locator", {})
                target = check["path"] + (":" + compact(loc) if loc else diff["actual_source"]["json_pointer"])
                actual = compact(diff["actual"]) if diff["actual_present"] else "未取得/无法解析"
                expected = compact(diff["expected"]) if diff["expected_present"] else "不应存在"
                lines.append(f"- `{check['id']}` `{target}`：实际 `{actual}`；期望 `{expected}`（{diff['kind']}）。")
        propagation_record = row["cross_artifact_error_links"]
        if propagation_record:
            lines += ["", propagation_record["interpretation"], ""]
            for link in propagation_record["same_named_field_delta_links"]:
                lines.append(f"- `{link['field']}` 台账差额合计 {link['ledger_field_delta_sum']:+d}，汇总差额 {link['summary_delta']:+d}；{'算术相容' if link['arithmetic_equal'] else '差额不同'}。")
            lines += ["", "这些是相关结果位置，不证明一个共同根因；旧台账整块失分仍保留。"]
        lines.append("")
    lines += ["## 声明与业务结果分开", "",
              "| 用例 | 冻结检查的解释分类（仍用旧60分权重） |", "|---|---|"]
    for case_id in ("T01", "T02", "T03", "T04", "T05"):
        row = next(row for row in report["runs"] if row["case_id"] == case_id)
        groups = row["check_classification_old_weight_only"]
        lines.append("| " + case_id + " | " + "；".join(f"{key} {value['maximum_in_old_60']:g}/60" for key, value in groups.items()) + " |")
    lines += ["", "T04 incident正确只说明18/60声明字段匹配；是否真实请求补发以过程引用核验。T05 source_audit的21/60为来源登记、忽略、适用规则及无外传声明，禁词检查另占3/60；均不证明无外传。T03修改清单/未修改声明12/60不能替代实际文件，T02引文及冲突声明不替代真实执行追踪。", "",
              "## 五产品共同E2观察", "",
              "每项的置信、未知范围及旧review具体公共refs列在JSON `common_e2_matrix`。下表为有记录入口的端到端观察，归因均unresolved；无新分。", "",
              "| 产品 | T01/T02/T03/T04/T05所需原件 | T03原生交付结构 | T04请求、补发与续接 |", "|---|---|---|---|"]
    for product in report["common_e2_matrix"]:
        cases = sorted(product["cases"], key=lambda c: c["case_id"])
        files = "/".join("已取" if not c["real_files_obtainable"]["missing_paths"] else "未取" for c in cases)
        t03 = next(c for c in cases if c["case_id"] == "T03")
        t04 = next(c for c in cases if c["case_id"] == "T04")
        lines.append(f"| {product['product_id']} | {files} | {t03['native_delivery_structure']['note']} | {t04['t04_request_release_continuation']['note']} |")
    lines += ["", "E2的原件存在性置信高（仅所引本地字节）；原生结构/可见续接为公共采集来源的中等置信，远端内部过程未知。豆包T03平铺原件正确与目录重组分别报告；元宝T03未取得交付只描述复查现场，不推断远端内部从未生成。", "",
              "E1额外审计在JSON单列：Codex/DSH有更多公开执行投影，WB/元宝/豆包主要是普通UI与文件。每条列具体公共引用与可见事件类型；未采集执行流保持未知，不据CLI丰富日志降低GUI分，也不把声明当完整自验。", "",
              "## 范围与历史辅助", "",
              "25组合为后验单次选取；31原包、先前调试与额外豆包本地失败不删除、不改选。模型、Skill、权限、入口及环境不匹配，不支持纯Harness因果排名或一般表现估计。缺失文件按路径报告，无法解析按检查报告；差异计数没有跨题共同字段分母，也不视作独立错误数。", "",
              report["historical_auxiliary_only"]["interpretation"], "",
              report["historical_auxiliary_only"]["weight_sensitivity"], "",
              "旧均值仅作原值索引：", "", "| 产品 | 旧最终原件均分 /60 | 旧综合算术范围（历史辅助） |", "|---|---:|---|"]
    for aggregate in report["historical_auxiliary_only"]["aggregates_unchanged"]:
        lines.append(f"| {aggregate['product_id']} | {aggregate['objective_mean']:g} | {compact(aggregate['descriptive_mean_range'])} |")
    lines += ["", "复算：`python scripts/analyze_evaluation_v2.py --check`。脚本仅写本派生JSON/MD，不启动产品、不读取private、不使用动态时间。哈希只定位版本，不证明记录真实完整。", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare generated bytes with the two reports without writing")
    args = parser.parse_args(argv)
    report = build_report()
    artifacts = {ROOT / "reports/evaluation-v2.json": json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                 ROOT / "reports/evaluation-v2.md": markdown(report)}
    mismatches = []
    for path, content in artifacts.items():
        payload = content.encode("utf-8")
        if args.check:
            if not path.is_file() or path.read_bytes() != payload:
                mismatches.append(path.name)
        else:
            path.write_bytes(payload)
    if mismatches:
        print("Stale derived reports: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print(("Verified" if args.check else "Generated") + " evaluation-v2.json / evaluation-v2.md; 25 historical selected episodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
