"""Strict deterministic artifact checks and evidence gates, using only the stdlib."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"file_exists", "exact_json", "json_fields", "csv_rows", "bytes_equal",
         "text_contains", "text_excludes"}
FINAL_STATUSES = {"completed", "failed", "timeout", "unsupported", "infra_error"}


def parse_time(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("事件时间必须含时区")
    return parsed


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def expected_snapshot():
    files = []
    for folder in ("harness_eval", "cases"):
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.suffix != ".pyc")
    files.extend(ROOT / name for name in (
        "config/protocol.json", "config/rubric.json", "config/products.json", "docs/protocol.md",
        "docs/attribution.md", "docs/rubric.md"))
    if any(not p.is_file() for p in files):
        raise ValueError("方案/归因/评分文档尚未齐备，不能建立实验包")
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(files)}


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"重复 JSON 键: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    def reject_constant(value):
        raise ValueError(f"非法 JSON 数值: {value}")
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_pairs,
                      parse_constant=reject_constant)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("路径必须是非空相对路径")
    base = root.resolve()
    target = (base / relative).resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError(f"路径越界: {relative}")
    return target


def inventory(root: Path, exclude=()) -> dict:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()) \
                or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"不允许证据包含链接或越界路径: {path}")
        name = path.relative_to(root).as_posix()
        if path.is_file() and name not in exclude:
            result[name] = sha256(path)
    return result


def json_equal(actual, expected) -> bool:
    # Python's True == 1 would otherwise award points for a wrong JSON type.
    return json.dumps(actual, sort_keys=True, ensure_ascii=False, allow_nan=False) == \
        json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False)


def load_case(case_dir: Path):
    case = read_json(case_dir / "case.json")
    if case["id"] != case_dir.name:
        raise ValueError(f"用例 ID 与目录不一致: {case_dir}")
    checks = case["checks"]
    if not checks or len({c["id"] for c in checks}) != len(checks):
        raise ValueError("检查 ID 必须唯一且不能为空")
    if any(type(c["weight"]) not in (int, float) or not math.isfinite(c["weight"])
           or c["weight"] <= 0 for c in checks):
        raise ValueError("检查权重必须为有限正数")
    if sum(c["weight"] for c in checks) != 100:
        raise ValueError("每用例检查权重之和必须为 100")
    oracle = read_json(inside(case_dir, case["oracle_file"]))
    if not inside(case_dir, case["prompt_file"]).is_file():
        raise ValueError("缺任务提示词")
    if not inside(case_dir, case["input_dir"]).is_dir():
        raise ValueError("缺任务输入目录")
    for check in checks:
        if check["kind"] not in KINDS:
            raise ValueError(f"未知检查类型: {check['kind']}")
        cfg = check["config"]
        inside(case_dir / "hypothetical_outputs", cfg["path"])
        if "oracle_key" in cfg and cfg["oracle_key"] not in oracle:
            raise ValueError(f"缺预期答案: {cfg['oracle_key']}")
        if check["kind"] == "bytes_equal" and not inside(case_dir, cfg["reference"]).is_file():
            raise ValueError("缺字节比对参考文件")
    for name in case["required_outputs"]:
        inside(case_dir / "hypothetical_outputs", name)
    return case, oracle


def _csv_rows(path: Path, keys: list[str], expected: list[dict]) -> bool:
    if not expected:
        raise ValueError("CSV oracle 需要至少一行以定义列")
    columns = set(expected[0])
    if not keys or not set(keys) <= columns:
        raise ValueError("CSV 主键配置无效")
    if any(set(row) != columns or any(not isinstance(v, str) for v in row.values())
           for row in expected):
        raise ValueError("CSV oracle 列必须一致，值必须是字符串")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)) or set(headers) != columns:
            return False
        actual = list(reader)
    if any(set(row) != columns or any(value is None for value in row.values())
           for row in actual):
        return False
    def indexed(rows):
        result = {}
        for row in rows:
            key = tuple(row[k] for k in keys)
            if key in result:
                raise ValueError(f"CSV 主键重复: {key}")
            result[key] = row
        return result
    return indexed(actual) == indexed(expected)


def check_artifact(check: dict, case_dir: Path, outputs: Path, oracle: dict) -> dict:
    cfg, kind = check["config"], check["kind"]
    result = {"id": check["id"], "title": check["title"], "weight": check["weight"],
              "path": cfg["path"], "passed": False, "reason": "", "sha256": None,
              "confidence": "high",
              "confidence_basis": "按冻结检查参数与标准答案确定性核验指定文件；"
                                  "置信只针对该文件/路径，不证明执行过程或Harness归因",
              "attribution": "unresolved"}
    try:
        path = inside(outputs, cfg["path"])
        if not path.is_file():
            result["reason"] = "交付文件缺失"
            return result
        result["sha256"] = sha256(path)
        if kind == "file_exists":
            passed = True
        elif kind == "exact_json":
            passed = json_equal(read_json(path), oracle[cfg["oracle_key"]])
        elif kind == "json_fields":
            actual, expected = read_json(path), oracle[cfg["oracle_key"]]
            passed = isinstance(actual, dict) and isinstance(expected, dict) and all(
                key in actual and json_equal(actual[key], value) for key, value in expected.items())
        elif kind == "csv_rows":
            passed = _csv_rows(path, cfg["key_columns"], oracle[cfg["oracle_key"]])
        elif kind == "bytes_equal":
            passed = path.read_bytes() == inside(case_dir, cfg["reference"]).read_bytes()
        elif kind in {"text_contains", "text_excludes"}:
            content = path.read_text(encoding="utf-8-sig")
            values = cfg["values"]
            passed = all(v in content for v in values) if kind == "text_contains" else \
                all(v not in content for v in values)
        else:
            raise ValueError(f"未知检查类型: {kind}")
        result["passed"] = bool(passed)
        result["reason"] = "满足预注册判定" if passed else "不满足预注册判定"
    except (ValueError, KeyError, TypeError, OSError, csv.Error) as exc:
        result["reason"] = f"格式或内容无效: {exc}"
    return result


def evaluate(case_dir: Path, outputs: Path, objective_weight=60) -> dict:
    case, oracle = load_case(case_dir)
    checks = [check_artifact(c, case_dir, outputs, oracle) for c in case["checks"]]
    passed = sum(c["weight"] for c in checks if c["passed"])
    return {"case_id": case["id"], "checks": checks,
            "passed_weight": passed, "all_weight": 100,
            "objective_score": round(objective_weight * passed / 100, 4),
            "all_required_outputs_present": all(
                inside(outputs, name).is_file() for name in case["required_outputs"]),
            "all_checks_passed": all(c["passed"] for c in checks)}


def read_events(run: Path) -> list[dict]:
    path = run / "events.jsonl"
    events, ids = [], set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line, object_pairs_hook=_pairs)
        instant = parse_time(event["at"])
        if events and instant < parse_time(events[-1]["at"]):
            raise ValueError(f"事件时间倒退，行 {line_no}")
        if event.get("id") in ids or not event.get("id"):
            raise ValueError(f"事件 ID 重复或缺失，行 {line_no}")
        ids.add(event["id"])
        if not isinstance(event.get("summary"), str) or not event["summary"].strip():
            raise ValueError(f"事件缺说明，行 {line_no}")
        if not isinstance(event.get("evidence"), list):
            raise ValueError(f"事件证据格式错误，行 {line_no}")
        for ref in event["evidence"]:
            path = inside(run, ref["path"])
            if not path.is_file() or sha256(path) != ref["sha256"]:
                raise ValueError(f"事件证据缺失或已改变: {ref['path']}")
        events.append(event)
    return events


def validate_run(run: Path, require_sealed=True) -> tuple[dict, list[dict]]:
    meta = read_json(run / "meta.json")
    protocol = read_json(ROOT / "config/protocol.json")
    if meta.get("product_id") not in protocol["product_ids"]:
        raise ValueError("产品 ID 无效")
    if meta.get("case_id") not in protocol["case_ids"]:
        raise ValueError("用例 ID 无效")
    if type(meta.get("replicate")) is not int or not 1 <= meta["replicate"] <= protocol["replicates"]:
        raise ValueError("重复序号无效")
    if meta.get("status") not in FINAL_STATUSES | {"pending"}:
        raise ValueError("运行状态无效")
    if meta.get("track") not in {"product_default", "pilot", "attribution"}:
        raise ValueError("实验轨道无效")
    expected_id = f"{meta['track']}-{meta['product_id']}-{meta['case_id']}-r{meta['replicate']}"
    if meta.get("run_id") != expected_id:
        raise ValueError("实验ID与产品/任务/重复号不一致")
    if meta.get("wall_clock_seconds") != protocol["wall_clock_seconds"] \
            or meta.get("network") != protocol["network"]:
        raise ValueError("运行预算或联网条件与冻结协议不一致")
    snapshot = read_json(run / "evaluation_snapshot.json")
    if snapshot != expected_snapshot() or meta.get("config_fingerprint") != fingerprint(snapshot):
        raise ValueError("冻结快照缺失、文件发生变化或指纹无效")
    for name, digest in snapshot.items():
        path = inside(ROOT, name)
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"评测配置/代码/用例发生变化，需新建实验批次: {name}")
    case_dir = ROOT / "cases" / meta["case_id"]
    case, _ = load_case(case_dir)
    canonical_inputs = {"prompt.md": sha256(inside(case_dir, case["prompt_file"])), **{
        "inputs/" + name: digest for name, digest in inventory(
            inside(case_dir, case["input_dir"])).items()}}
    if meta.get("participant_input_hashes") != canonical_inputs:
        raise ValueError("登记的初始输入与冻结用例不一致")
    for name, digest in meta["participant_input_hashes"].items():
        path = inside(run / "workspace", name)
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"参与者输入发生变化: {name}")
    allowed = {k.removeprefix("inputs/") for k in meta["participant_input_hashes"]
               if k.startswith("inputs/")}
    allowed |= set(meta.get("released_files", {}))
    actual = inventory(run / "workspace/inputs")
    if set(actual) != allowed:
        raise ValueError("输入包出现未登记的新增或缺失文件")
    for name, digest in meta.get("released_files", {}).items():
        if actual.get(name) != digest:
            raise ValueError(f"补发输入发生变化: {name}")
        permitted = {item["attachment_name"]: sha256(inside(case_dir, item["source"]))
                     for item in case.get("release_protocol", {}).get("release_files", [])}
        if name not in permitted or digest != permitted[name]:
            raise ValueError(f"补发输入与冻结协议不一致: {name}")
    events = read_events(run)
    starts = [e for e in events if e["kind"] == "start"]
    finishes = [e for e in events if e["kind"] == "finish"]
    if len(starts) > 1 or len(finishes) > 1:
        raise ValueError("开始/结束事件重复")
    if events and (not starts or starts[0] is not events[0]):
        raise ValueError("开始必须是首个事件")
    if starts and parse_time(meta["started_at"]) != parse_time(starts[0]["at"]):
        raise ValueError("元数据开始时间与现场事件不一致")
    if finishes and finishes[0] is not events[-1]:
        raise ValueError("结束之后不能追加任务事件")
    if meta.get("unscheduled_interventions") != sum(e["kind"] == "intervention" for e in events):
        raise ValueError("人工干预计数与事件不一致")
    if meta.get("scheduled_interventions") != sum(e["kind"] == "scheduled_release" for e in events):
        raise ValueError("预定补发计数与事件不一致")
    if meta["status"] in FINAL_STATUSES:
        if not starts or not finishes:
            raise ValueError("运行终态缺少开始/结束现场事件")
        if parse_time(meta["ended_at"]) != parse_time(finishes[0]["at"]):
            raise ValueError("结束时间与最后现场事件不一致")
        seconds = (parse_time(meta["ended_at"]) - parse_time(meta["started_at"])).total_seconds()
        if meta.get("elapsed_seconds") != seconds or seconds < 0:
            raise ValueError("运行时长无效")
        if meta["status"] == "completed" and seconds > protocol["wall_clock_seconds"]:
            raise ValueError("完成运行超出墙钟预算")
        if meta["unscheduled_interventions"] > protocol["max_unscheduled_interventions"] \
                and meta["status"] != "failed":
            raise ValueError("人工干预超预算应标为failed并披露协议偏离")
    if require_sealed:
        manifest = read_json(run / "manifest.json")
        if inventory(run, exclude=("manifest.json",)) != manifest["files"]:
            raise ValueError("封存后证据包已发生变化，请核对并重新封存")
        if manifest.get("schema_version") != 1:
            raise ValueError("封存格式无效")
    return meta, events


def score_run(run: Path) -> dict:
    meta, events = validate_run(run)
    rubric = read_json(ROOT / "config/rubric.json")
    result = {"run_id": meta["run_id"], "product_id": meta["product_id"],
              "replicate": meta["replicate"], "track": meta["track"],
              "status": meta["status"], "config_fingerprint": meta["config_fingerprint"],
              "evidence_package_sha256": sha256(run / "manifest.json"),
              "protocol_status": read_json(ROOT / "config/protocol.json")["status"]}
    result["runtime_config"] = {key: meta.get(key) for key in (
        "product_version", "model", "model_visibility", "skill_condition", "surface",
        "network", "wall_clock_seconds", "mode", "account_tier", "region",
        "memory_condition", "permissions", "environment")}
    result.update(evaluate(ROOT / "cases" / meta["case_id"], run / "workspace/outputs",
                           rubric["objective_weight"]))
    if meta["status"] == "unsupported" and result["objective_score"] != 0:
        raise ValueError("unsupported运行包含得分产物，应核对并登记为failed或completed")
    result["score_scope"] = "产品配置端到端；分数本身不隔离模型/Skill/Harness影响"
    result["missing_evidence"] = []
    result["manual_scores"] = []
    if meta["unscheduled_interventions"] > read_json(ROOT / "config/protocol.json")["max_unscheduled_interventions"]:
        result["missing_evidence"].append("人工干预超预算，保留偏离记录但不发布总分")
    if meta["status"] in {"pending", "infra_error"}:
        result["total_score"] = None
        result["eligible"] = False
        result["missing_evidence"].append("未采集或外部实验环境故障，不进入主分母")
        return result
    for key in ("product_version", "model", "skill_condition", "surface", "operator"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            result["missing_evidence"].append(f"未记录运行条件: {key}")
    if not meta.get("started_at") or not meta.get("ended_at"):
        result["missing_evidence"].append("缺开始/结束时间")
    if not any(e.get("kind") == "start" and e.get("evidence") for e in events):
        result["missing_evidence"].append("缺带现场证据的开始事件")
    if not any(e.get("kind") == "finish" and e.get("evidence") for e in events):
        result["missing_evidence"].append("缺带现场证据的结束事件")
    by_id = {e["id"]: e for e in events}
    manual = read_json(run / "manual.json")
    dimensions = manual.get("dimensions", {})
    for spec in rubric["manual_dimensions"]:
        item = dimensions.get(spec["id"], {})
        issues = []
        if type(item.get("grade")) is not int or item["grade"] not in rubric["grade_scale"]:
            issues.append("缺0到4的整数等级")
        for key in ("reason", "confidence_basis", "alternative_explanation", "reviewer"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                issues.append(f"缺{key}")
        if item.get("confidence") not in rubric["confidence_levels"]:
            issues.append("缺置信等级")
        if item.get("attribution") not in rubric["attribution_labels"]:
            issues.append("缺归因标签")
        refs = item.get("event_ids", [])
        if not isinstance(refs, list) or not refs or any(
                ref not in by_id or not by_id[ref].get("evidence") for ref in refs):
            issues.append("缺有效现场事件证据")
        if issues:
            result["missing_evidence"].append(spec["id"] + ": " + "; ".join(issues))
        else:
            result["manual_scores"].append({**spec, **item,
                                           "score": spec["weight"] * item["grade"] / 4})
    result["eligible"] = not result["missing_evidence"]
    result["total_score"] = round(result["objective_score"] + sum(
        s["score"] for s in result["manual_scores"]), 4) if result["eligible"] else None
    return result
