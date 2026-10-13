"""python -m harness_eval --help"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core import (ROOT, FINAL_STATUSES, evaluate, expected_snapshot, fingerprint,
                   inside, inventory, load_case,
                   read_events, read_json, score_run, sha256, validate_run, write_json)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("时间必须含时区，如 2026-10-13T10:00:00+08:00")
    return parsed


def snapshot():
    return expected_snapshot()


def manual_template():
    rubric = read_json(ROOT / "config/rubric.json")
    return {"dimensions": {s["id"]: {
        "grade": None, "reason": "", "event_ids": [], "confidence": None,
        "confidence_basis": "", "alternative_explanation": "",
        "attribution": "unresolved", "reviewer": ""
    } for s in rubric["manual_dimensions"]}}


def command_audit(args):
    protocol = read_json(ROOT / "config/protocol.json")
    rubric = read_json(ROOT / "config/rubric.json")
    if rubric["objective_weight"] + sum(s["weight"] for s in rubric["manual_dimensions"]) != 100:
        raise ValueError("评分权重之和不是100")
    products = read_json(ROOT / "config/products.json")["products"]
    if set(p["id"] for p in products) != set(protocol["product_ids"]):
        raise ValueError("产品登记与协议不一致")
    for case_id in protocol["case_ids"]:
        case, _ = load_case(ROOT / "cases" / case_id)
        print(f"{case_id}: {len(case['checks'])} checks, 100 weight, {case['title']}")
    print("配置检查通过；这不代表任何产品已经运行。")


def command_plan(args):
    protocol = read_json(ROOT / "config/protocol.json")
    rng = random.Random(protocol["seed"])
    blocks = [(rep, case_id) for rep in range(1, protocol["replicates"] + 1)
              for case_id in protocol["case_ids"]]
    rng.shuffle(blocks)
    slots = []
    for rep, case_id in blocks:
        products = list(protocol["product_ids"])
        rng.shuffle(products)
        for product in products:
            slots.append({"order": len(slots) + 1, "product_id": product, "case_id": case_id,
                          "replicate": rep, "track": protocol["track"]})
    path = Path(args.out)
    if path.exists():
        raise ValueError("计划文件已存在；请保留原计划或使用新的文件名")
    write_json(path, {"protocol_id": protocol["protocol_id"], "seed": protocol["seed"],
                      "created_at": now(), "evaluation_fingerprint": fingerprint(snapshot()),
                      "runs": slots})
    print(f"已写入{len(slots)}个待执行实验位: {path.resolve()}")


def command_prepare(args):
    protocol = read_json(ROOT / "config/protocol.json")
    if args.product not in protocol["product_ids"] or args.case not in protocol["case_ids"]:
        raise ValueError("未知产品或任务")
    if not 1 <= args.replicate <= protocol["replicates"]:
        raise ValueError("重复序号超出范围")
    case_dir = ROOT / "cases" / args.case
    case, _ = load_case(case_dir)
    run_id = f"{args.track}-{args.product}-{args.case}-r{args.replicate}"
    run = Path(args.runs_dir) / run_id
    if run.exists():
        raise ValueError("实验目录已存在，禁止覆盖或挑选较好的结果")
    frozen = snapshot()
    run.mkdir(parents=True)
    workspace = run / "workspace"
    workspace.mkdir()
    shutil.copytree(inside(case_dir, case["input_dir"]), workspace / "inputs")
    shutil.copyfile(inside(case_dir, case["prompt_file"]), workspace / "prompt.md")
    (workspace / "outputs").mkdir()
    (run / "evidence").mkdir()
    (run / "events.jsonl").write_text("", encoding="utf-8")
    write_json(run / "manual.json", manual_template())
    write_json(run / "evaluation_snapshot.json", frozen)
    write_json(run / "meta.json", {
        "schema_version": 1, "run_id": run_id, "product_id": args.product,
        "case_id": args.case, "replicate": args.replicate, "track": args.track,
        "status": "pending", "created_at": now(), "started_at": None, "ended_at": None,
        "operator": None, "surface": None, "product_version": None, "model": None,
        "mode": None, "account_tier": None, "region": None, "memory_condition": None,
        "permissions": None, "environment": None,
        "model_visibility": "unknown", "skill_condition": None,
        "network": protocol["network"], "wall_clock_seconds": protocol["wall_clock_seconds"],
        "unscheduled_interventions": 0, "scheduled_interventions": 0,
        "recording_limitations": "", "redaction_reviewed": False,
        "status_reason": "", "config_fingerprint": fingerprint(frozen),
        "participant_input_hashes": {"prompt.md": sha256(workspace / "prompt.md"), **{
            "inputs/" + name: digest for name, digest in inventory(workspace / "inputs").items()}},
        "released_files": {}
    })
    print(f"待采集实验包: {run.resolve()}")
    print(f"仅将这个目录交给产品: {workspace.resolve()}")


def append_event(run, kind, summary, evidence, at=None):
    meta = read_json(run / "meta.json")
    if (run / "manifest.json").exists():
        raise ValueError("实验已封存，不能追加事件")
    if meta["status"] != "pending":
        raise ValueError("运行已结束，不能继续追加任务事件")
    events = read_events(run)
    if any(e["kind"] == "finish" for e in events):
        raise ValueError("结束事件已登记，不能继续追加任务事件")
    instant = at or now()
    timestamp(instant)
    if events and timestamp(instant) < timestamp(events[-1]["at"]):
        raise ValueError("事件时间倒退，需按发生顺序登记")
    refs = []
    for name in evidence:
        path = inside(run, name)
        if not path.is_file():
            raise ValueError(f"证据文件不存在: {name}")
        refs.append({"path": path.relative_to(run.resolve()).as_posix(), "sha256": sha256(path)})
    event = {"id": f"E{len(events) + 1:03d}", "at": instant, "kind": kind,
             "summary": summary, "evidence": refs, "origin": "operator_record"}
    if kind == "start":
        if meta["started_at"]:
            raise ValueError("不能重复登记开始")
        meta["started_at"] = instant
    elif not meta["started_at"]:
        raise ValueError("先登记 start 事件")
    if kind == "intervention":
        meta["unscheduled_interventions"] += 1
    if kind == "scheduled_release":
        meta["scheduled_interventions"] += 1
    with (run / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    write_json(run / "meta.json", meta)
    return event


def command_event(args):
    print(append_event(Path(args.run).resolve(), args.kind, args.summary,
                       args.evidence, args.at)["id"])


def command_release(args):
    run = Path(args.run).resolve()
    meta, events = validate_run(run, require_sealed=False)
    if meta["status"] != "pending" or not meta["started_at"] or (run / "manifest.json").exists():
        raise ValueError("仅能在开始后、结束前补发")
    if meta["case_id"] != "T04":
        raise ValueError("只有T04允许协议补发")
    case, _ = load_case(ROOT / "cases/T04")
    release_protocol = case["release_protocol"]
    allowed_files = {item["attachment_name"] for item in release_protocol["release_files"]}
    if args.file not in allowed_files or meta["scheduled_interventions"] >= release_protocol["max_releases"]:
        raise ValueError("补发文件或补发次数不符合用例协议")
    instant = args.at or now()
    if any(e["kind"] == "finish" for e in events):
        raise ValueError("结束事件已登记，不能补发")
    if events and timestamp(instant) < timestamp(events[-1]["at"]):
        raise ValueError("补发时间早于最近现场事件")
    seconds = (timestamp(instant) - timestamp(meta["started_at"])).total_seconds()
    deadline = release_protocol["trigger"]["request_deadline_seconds"]
    if seconds < 0 or seconds > meta["wall_clock_seconds"]:
        raise ValueError("补发不在运行时间预算内")
    if args.mode == "passive" and seconds < deadline:
        raise ValueError("未到120秒，不允许提前被动补发")
    if args.mode == "active":
        request = next((e for e in events if e["id"] == args.request_event), None)
        if not request or not request["evidence"]:
            raise ValueError("主动补发须引用带实际请求证据的事件")
        request_seconds = (timestamp(request["at"]) - timestamp(meta["started_at"])).total_seconds()
        if not 0 <= request_seconds <= deadline or timestamp(request["at"]) > timestamp(instant):
            raise ValueError("主动请求不在协议窗口内，或晚于补发")
    source = inside(ROOT / "cases/T04/releases", args.file)
    if not source.is_file() or source.suffix != ".json":
        raise ValueError("请选择协议定义的JSON补发输入")
    target = inside(run / "workspace/inputs", args.file)
    if target.exists():
        raise ValueError("补发文件已存在，禁止覆盖")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    name = target.relative_to(run / "workspace/inputs").as_posix()
    meta["released_files"][name] = sha256(target)
    write_json(run / "meta.json", meta)
    receipt = "evidence/release-receipt.json"
    write_json(run / receipt, {"action": "复制协议补发文件至参与者输入目录",
                               "file": name, "sha256": sha256(target), "at": instant,
                               "mode": args.mode, "request_event": args.request_event,
                               "response_text": release_protocol["response_text"], "note": args.note})
    event = append_event(run, "scheduled_release", args.note, [receipt], instant)
    print(f"{event['id']}: 已补发{name}。界面上传/用户回复仍需现场记录。")


def command_finalize(args):
    run = Path(args.run).resolve()
    meta, events = validate_run(run, require_sealed=False)
    if (run / "manifest.json").exists() or meta["status"] != "pending":
        raise ValueError("实验已结束或封存")
    if not meta["started_at"] or not any(e["kind"] == "finish" for e in events):
        raise ValueError("先登记 start 与带结果证据的 finish 事件")
    ended = args.at or events[-1]["at"]
    if events[-1]["kind"] != "finish" or timestamp(ended) != timestamp(events[-1]["at"]):
        raise ValueError("结束时间必须与最后的finish现场事件一致")
    seconds = (timestamp(ended) - timestamp(meta["started_at"])).total_seconds()
    if seconds < 0:
        raise ValueError("结束时间早于开始")
    if seconds > meta["wall_clock_seconds"] and args.status == "completed":
        raise ValueError("已超墙钟预算，必须标为timeout并仅保留截至预算的产物")
    protocol = read_json(ROOT / "config/protocol.json")
    if meta["unscheduled_interventions"] > protocol["max_unscheduled_interventions"] and args.status != "failed":
        raise ValueError("超出人工干预预算，应保留预算内产物并登记failed")
    if not isinstance(args.note, str) or not args.note.strip():
        raise ValueError("请记录实际终态原因")
    meta.update(status=args.status, ended_at=ended, elapsed_seconds=seconds, status_reason=args.note)
    write_json(run / "meta.json", meta)
    validate_run(run, require_sealed=False)
    print("运行已结束；填写manual.json后运行seal封存，再评分。")


def command_seal(args):
    run = Path(args.run).resolve()
    meta, _ = validate_run(run, require_sealed=False)
    if meta["status"] == "pending":
        raise ValueError("未采集实验不能封存为结果")
    if (run / "manifest.json").exists():
        raise ValueError("已有封存；修改证据应另建更正记录，禁止静默重封")
    write_json(run / "manifest.json", {"schema_version": 1, "sealed_at": now(),
                                       "files": inventory(run, exclude=("manifest.json",))})
    print(f"证据已封存: {run.resolve()}")


def command_verify(args):
    result = evaluate(ROOT / "cases" / args.case, Path(args.outputs).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_checks_passed"] else 1


def command_score(args):
    result = score_run(Path(args.run).resolve())
    path = Path(args.out) if args.out else ROOT / "reports/scores" / (result["run_id"] + ".json")
    if path.resolve().is_relative_to(Path(args.run).resolve()):
        raise ValueError("评分结果必须写在封存证据包之外")
    write_json(path, result)
    print(f"产物分: {result['objective_score']}/60; 总分: {result['total_score']}; {path.resolve()}")
    for problem in result["missing_evidence"]:
        print("待补证据: " + problem)
    return 0 if result["eligible"] else 2


def command_export(args):
    run, target = Path(args.run).resolve(), Path(args.out).resolve()
    meta, _ = validate_run(run)
    if not meta.get("redaction_reviewed"):
        raise ValueError("先人工审查待公开证据，在meta中记录redaction_reviewed=true，然后封存")
    if target.exists() or target.is_relative_to(run):
        raise ValueError("公开副本目标必须是证据包外的新目录")
    shutil.copytree(run, target)
    print(f"已创建本地公开副本，未上传: {target}")


def command_report(args):
    protocol = read_json(ROOT / "config/protocol.json")
    records = []
    for path in sorted(Path(args.runs_dir).glob("*/meta.json")):
        run = path.parent
        meta = read_json(path)
        if meta.get("track") != "product_default":
            continue
        if meta.get("status") == "pending":
            records.append({"run_id": meta["run_id"], "product_id": meta["product_id"],
                            "case_id": meta["case_id"], "replicate": meta["replicate"],
                            "status": "pending", "total_score": None, "eligible": False})
        else:
            result = score_run(run)
            result["evidence_directory"] = str(run.resolve())
            records.append(result)
    seen = {}
    for record in records:
        key = (record["product_id"], record["case_id"], record["replicate"])
        if record["status"] != "infra_error":
            if key in seen:
                raise ValueError(f"同一实验位存在重复结果，不能挑选: {key}")
            seen[key] = record
    lines = ["# 五款 Harness 竞品评测汇总", "",
             "本表由已封存的本地证据包计算。未采集的实验没有分数。", "",
             "分数衡量指定产品配置的端到端表现；Harness 因果结论须另附匹配对照。", "",
             f"协议状态：{protocol['status']}。draft/pilot结果不作为正式预注册主实验。", "",
             "| 产品 | 可评分/计划 | 产物全通过/已采集 | 完整主实验均分 |", "|---|---:|---:|---:|"]
    summary = []
    all_complete = protocol["status"] == "preregistered"
    for product in protocol["product_ids"]:
        eligible = [r for r in records if r["product_id"] == product and r["eligible"]]
        expected = len(protocol["case_ids"]) * protocol["replicates"]
        configs = {fingerprint(r.get("runtime_config", {})) for r in eligible}
        if len(eligible) != expected or len(configs) != 1:
            all_complete = False
    for product in protocol["product_ids"]:
        relevant = [r for r in records if r["product_id"] == product and r["status"] != "infra_error"]
        eligible = [r for r in relevant if r["eligible"]]
        collected = [r for r in relevant if r["status"] != "pending"]
        passed = sum(r.get("all_checks_passed", False) and r["status"] == "completed"
                     for r in collected)
        expected = len(protocol["case_ids"]) * protocol["replicates"]
        configs = {fingerprint(r.get("runtime_config", {})) for r in eligible}
        complete = all_complete
        means = []
        if complete:
            means = [sum(r["total_score"] for r in eligible if r["case_id"] == case_id)
                     / protocol["replicates"] for case_id in protocol["case_ids"]]
        mean = round(sum(means) / len(means), 2) if means else None
        label = str(mean) if mean is not None else "待完成或配置不一致"
        lines.append(f"| {product} | {len(eligible)}/{expected} | {passed}/{len(collected)} | {label} |")
        summary.append({"product_id": product, "eligible": len(eligible), "planned": expected,
                        "collected": len(collected), "artifact_passed": passed,
                        "mean_score": mean, "runtime_configs": len(configs)})
    lines.extend(["", "## 逐次结果与证据", "",
                  "| 实验 | 状态 | 产物分/60 | 总分/100 | 复核目录 |", "|---|---|---:|---:|---|"])
    for r in records:
        lines.append(f"| {r['run_id']} | {r['status']} | {r.get('objective_score', '—')} | "
                     f"{r['total_score'] if r['total_score'] is not None else '待证据'} | "
                     f"{r.get('evidence_directory', '待采集')} |")
    lines.extend(["", "## 结论状态", "", "研究者须在书面报告中逐项填写：观察、事件/产物引用、"
                  "得分理由、置信依据、替代解释、复核步骤。此汇总不自动生成能力判断或冠军。", "",
                  "平台不支持计入产品端到端分母；外部实验环境故障单列并补测。"
                  "尚缺过程证据时，仅产物分可计算，不用零分代替缺失记录。", ""])
    target = Path(args.out)
    if target.resolve().is_relative_to(Path(args.runs_dir).resolve()):
        raise ValueError("汇总应写在证据目录外")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    write_json(target.with_suffix(".json"), {"protocol": protocol, "products": summary, "runs": records})
    print(f"已生成汇总: {target.resolve()}")


def parser():
    cli = argparse.ArgumentParser(description="离线评测工具；不代替五产品实测")
    sub = cli.add_subparsers(dest="command", required=True)
    sub.add_parser("audit", help="检查评测配置与用例规格").set_defaults(func=command_audit)
    p = sub.add_parser("plan", help="生成随机区组顺序，禁止覆盖")
    p.add_argument("--out", default="reports/plan.json")
    p.set_defaults(func=command_plan)
    p = sub.add_parser("prepare", help="创建无答案的独立参与者工作区")
    p.add_argument("--product", required=True)
    p.add_argument("--case", required=True)
    p.add_argument("--replicate", type=int, default=1)
    p.add_argument("--track", choices=["product_default", "pilot", "attribution"], default="product_default")
    p.add_argument("--runs-dir", default="runs")
    p.set_defaults(func=command_prepare)
    p = sub.add_parser("event", help="登记现场事件，附真实证据文件")
    p.add_argument("--run", required=True)
    p.add_argument("--kind", choices=["start", "tool_call", "tool_result", "error", "user_message",
                                      "intervention", "artifact", "finish", "observation"], required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--at", help="原始发生时间，须含时区；默认当前UTC")
    p.set_defaults(func=command_event)
    p = sub.add_parser("release", help="复制T04的协议补发输入，记录补发回执")
    p.add_argument("--run", required=True)
    p.add_argument("--file", default="rates.json")
    p.add_argument("--note", required=True, help="记录触发条件与协议补发；另附上传现场证据")
    p.add_argument("--mode", choices=["active", "passive"], required=True)
    p.add_argument("--request-event", help="主动补发时引用实际请求的事件ID")
    p.add_argument("--at", help="真实补发时间，须含时区；默认当前UTC")
    p.set_defaults(func=command_release)
    p = sub.add_parser("finalize", help="登记运行终态，尚不封存")
    p.add_argument("--run", required=True)
    p.add_argument("--status", choices=sorted(FINAL_STATUSES), required=True)
    p.add_argument("--note", required=True)
    p.add_argument("--at")
    p.set_defaults(func=command_finalize)
    p = sub.add_parser("seal", help="封存元数据、过程和交付文件哈希")
    p.add_argument("--run", required=True)
    p.set_defaults(func=command_seal)
    p = sub.add_parser("verify", help="只验产物，不构成实际产品成绩")
    p.add_argument("--case", required=True)
    p.add_argument("--outputs", required=True)
    p.set_defaults(func=command_verify)
    p = sub.add_parser("score", help="从封存证据计算成绩")
    p.add_argument("--run", required=True)
    p.add_argument("--out")
    p.set_defaults(func=command_score)
    p = sub.add_parser("report", help="生成五产品汇总，无证据不生成排名")
    p.add_argument("--runs-dir", default="runs")
    p.add_argument("--out", default="reports/summary.md")
    p.set_defaults(func=command_report)
    p = sub.add_parser("export", help="创建经人工脱敏审查的本地公开证据副本")
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=command_export)
    return cli


def main():
    args = parser().parse_args()
    try:
        return args.func(args) or 0
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f"评测工具错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
