"""Audit boundary correspondences in already-redacted DSH public evidence.

Reads public packages only; writes derived reports. Never reads native/private
streams, repairs artifacts, gives a pure-Harness score, or upgrades pilot status.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIMITATIONS = [
    "Exploratory operation instances; each package is one episode, not one independent replicate per tool call.",
    "Checks compare published request projections with final artifact snapshots; they do not independently attest actual executor arguments.",
    "A differing snapshot may reflect truncation, later writes or mapping; it is not automatically a Harness failure.",
    "Later explicit write/edit calls exclude a write from final-byte comparison; shell, subagent and unseen mutations are not reconstructed.",
    "Model selection, Skill content, routing, tool implementation and environment are not matched across products.",
    "Error text/status correspondence does not identify the component that caused the error or chose a recovery path.",
    "Missing fields, inaccessible artifacts and unseen links remain unknown, never zero scores.",
    "Hash integrity is not authenticity; only already-redacted public evidence is read.",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {path.name}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique)


def path_inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or Path(relative).is_absolute():
        raise ValueError("Public manifest path escapes package")
    return path


def manifest_check(package):
    manifest = read_json(package / "manifest.json")
    entries = manifest.get("sha256", manifest.get("files", manifest))
    if isinstance(entries, list):
        entries = {entry["path"]: entry["sha256"] for entry in entries}
    if not isinstance(entries, dict):
        raise ValueError("Unsupported public manifest schema")
    hashes = {}
    for name, value in entries.items():
        expected = value.get("sha256") if isinstance(value, dict) else value
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Invalid manifest digest: {name}")
        path = path_inside(package, name)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError(f"Manifest mismatch: {name}")
        hashes[name] = expected
    present = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    unlisted = present - set(hashes) - {"manifest.json"}
    if unlisted:
        raise ValueError("Unmanifested public files: " + ", ".join(sorted(unlisted)))
    return {"verified": True, "file_count": len(hashes),
            "manifest_sha256": digest((package / "manifest.json").read_bytes())}


def reference(row, number):
    return {"public_line": number, "source_stdout_line": row.get("source_stdout_line"),
            "received_at": row.get("received_at"), "call_id": row["event"].get("callId")}


def output_relative(target):
    """Accept an explicit relative outputs/ path, without guessed prefixes."""
    if not isinstance(target, str):
        return None
    parts = target.replace("\\", "/").split("/")
    if not parts or parts[0].casefold() != "outputs":
        return None
    rest = parts[1:]
    if not rest or any(part in ("", ".", "..") for part in rest):
        return None
    return "/".join(rest)


def audit_episode(package, public_root):
    integrity = manifest_check(package)
    metadata = read_json(package / "run-metadata.json")
    rows = []
    for number, line in enumerate((package / "visible-events.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        event = row.get("event")
        if not isinstance(event, dict):
            raise ValueError("Unsupported visible event schema")
        if event.get("type") in ("thinking", "reasoning", "system"):
            raise ValueError("Unexpected non-public event type; review package before audit")
        rows.append((number, row))
    calls, results = defaultdict(list), defaultdict(list)
    writes, mutations = [], []
    for number, row in rows:
        event = row["event"]
        if event.get("type") == "tool_call":
            calls[event.get("callId")].append((number, row))
            if event.get("tool") == "write":
                writes.append((number, row))
            if event.get("tool") in ("write", "edit"):
                mutations.append((number, row))
        elif event.get("type") == "tool_result":
            results[event.get("callId")].append((number, row))
    write_observations = []
    for number, row in writes:
        event = row["event"]
        call_id = event.get("callId")
        parameters = event.get("input", {})
        parameters = parameters if isinstance(parameters, dict) else {}
        relative = output_relative(parameters.get("file_path"))
        item = {"request": reference(row, number), "artifact": f"outputs/{relative}" if relative else None,
                "verdict": "unknown", "reason": None, "requested_payload_sha256": None,
                "artifact_sha256": None, "attribution": "unresolved", "confidence": None}
        matching_results = results.get(call_id, [])
        if not isinstance(call_id, str) or not call_id or len(calls.get(call_id, [])) != 1 or len(matching_results) != 1:
            item["reason"] = "Request/result IDs absent or ambiguous"
        else:
            result_number, result_row = matching_results[0]
            item["result"] = reference(result_row, result_number)
            later_mutations = []
            for mutation_number, mutation_row in mutations:
                mutation = mutation_row["event"]
                mutation_input = mutation.get("input", {})
                mutation_relative = (output_relative(mutation_input.get("file_path"))
                                     if isinstance(mutation_input, dict) else None)
                # Conservatively treat case aliases as the same target for
                # this Windows evidence adapter; do not rewrite artifact paths.
                if relative is None or mutation_relative is None or mutation_relative.casefold() != relative.casefold():
                    continue
                if mutation_number == number:
                    continue
                mutation_id = mutation.get("callId")
                mutation_results = results.get(mutation_id, [])
                paired = (isinstance(mutation_id, str) and bool(mutation_id)
                          and len(calls.get(mutation_id, [])) == 1 and len(mutation_results) == 1
                          and mutation_results[0][0] > mutation_number)
                # Only a uniquely paired operation that finished before this
                # write began can be excluded as non-overlapping.
                if mutation_number < number and paired and mutation_results[0][0] < number:
                    continue
                observation = {"tool": mutation.get("tool"), "request": reference(mutation_row, mutation_number),
                               "state": "uncertain"}
                if paired:
                    observation["result"] = reference(mutation_results[0][1], mutation_results[0][0])
                    observation["native_status"] = mutation_results[0][1]["event"].get("status")
                    if mutation_number > result_number and observation["native_status"] == "completed":
                        observation["state"] = "completed_after_write"
                later_mutations.append(observation)
            if later_mutations:
                item["later_mutations"] = later_mutations
            if result_number <= number:
                item["reason"] = "Result precedes request in published stream"
            elif result_row["event"].get("status") != "completed":
                item["reason"] = "No completed write result; error handling is audited separately"
            elif relative is None:
                item["reason"] = "No explicit outputs/ target; no filename guessing or directory search"
            elif any(mutation["state"] == "uncertain" for mutation in later_mutations):
                item["reason"] = "A later or overlapping write/edit may have changed this target; final bytes cannot be assigned to this write"
            elif later_mutations:
                item["verdict"] = "superseded"
                item["reason"] = "A later uniquely paired completed write/edit targets the same file; intermediate bytes are unavailable"
            elif not isinstance(parameters.get("content"), str):
                item["reason"] = "Public string payload missing"
            else:
                artifact = path_inside(package, "outputs/" + relative)
                if not artifact.is_file():
                    item["reason"] = "Final artifact not published; intermediate write state cannot be reconstructed"
                else:
                    expected = digest(parameters["content"].encode("utf-8"))
                    actual = digest(artifact.read_bytes())
                    item.update(requested_payload_sha256=expected, artifact_sha256=actual,
                                verdict="match" if expected == actual else "different",
                                confidence="high for the published payload/final bytes comparison",
                                reason="Published UTF-8 request payload equals final artifact bytes" if expected == actual
                                else "Published payload differs from final snapshot; projection or later-change explanations remain")
        write_observations.append(item)
    error_observations = []
    for number, row in rows:
        event = row["event"]
        # Compare an explicit native failure text with its distinct status field.
        # Normal read results containing an Error: line inside a file do not qualify.
        if event.get("type") != "tool_result" or not isinstance(event.get("result"), str):
            continue
        text = event["result"]
        if not text.startswith("Error:"):
            continue
        call_id = event.get("callId")
        candidates = calls.get(call_id, [])
        item = {"result": reference(row, number), "verdict": "unknown", "tool": None,
                "failure_category": "other native Error: result", "native_status": event.get("status"),
                "attribution": "unresolved"}
        if "SetNamedSecurityInfoW" in text:
            item["failure_category"] = "Windows ACL grant failure"
        elif "no approval channel" in text:
            item["failure_category"] = "approval channel unavailable"
        if isinstance(call_id, str) and call_id and len(candidates) == 1 and len(results.get(call_id, [])) == 1 and candidates[0][0] < number:
            request_number, request_row = candidates[0]
            item["request"] = reference(request_row, request_number)
            item["tool"] = request_row["event"].get("tool")
            if isinstance(event.get("status"), str):
                item["verdict"] = "explicit_error" if event["status"] == "error" else "status_inconsistent"
                item["confidence"] = "high for public failure-text/status correspondence only"
            else:
                item["reason"] = "Native status field absent; not a failure verdict"
        else:
            item["reason"] = "Native request/result cannot be uniquely paired"
        error_observations.append(item)
    write_counts = Counter(item["verdict"] for item in write_observations)
    error_counts = Counter(item["verdict"] for item in error_observations)
    return {
        "episode_id": package.name, "package": package.relative_to(public_root).as_posix(),
        "product_id": "dsh", "case_id": metadata.get("case_id", metadata.get("case")),
        "track": metadata.get("track"), "surface": metadata.get("surface"),
        "formal_eligible": False, "pure_harness_score": None,
        "manifest": integrity, "visible_event_count": len(rows),
        "metrics": {
            "final_write_payload_artifact_correspondence": {
                "observed_write_instances": len(write_observations),
                "comparable_final_instances": write_counts["match"] + write_counts["different"],
                "matching_instances": write_counts["match"], "differing_instances": write_counts["different"],
                "unknown_instances": write_counts["unknown"], "superseded_instances": write_counts["superseded"],
                "denominator": "Completed public write to an explicit output target, with unique request/result, string content and final artifact, and no later or overlapping visible write/edit to that target",
                "interpretation": "Published projection/final snapshot correspondences, not a causal score or proof of executor fidelity",
                "instances": write_observations,
            },
            "explicit_error_status_projection": {
                "observed_failure_text_instances": len(error_observations),
                "paired_failure_instances": error_counts["explicit_error"] + error_counts["status_inconsistent"],
                "explicit_error_instances": error_counts["explicit_error"],
                "status_inconsistent_instances": error_counts["status_inconsistent"],
                "unknown_instances": error_counts["unknown"],
                "denominator": "Native tool_result text starts Error: and has exactly one preceding request and one result with the same ID",
                "interpretation": "Error feedback visibility only; no error-root-cause or recovery-policy attribution",
                "instances": error_observations,
            },
        },
    }


def render_markdown(report, destination, public_root):
    lines = ["# Harness 执行边界的探索性观察", "",
             "此表由已脱敏的真实公开证据独立生成。没有读取private原始流、修改产品产物或追认正式实验。"
             "这些是操作实例的对应检查；每个公开包只是一轮episode，工具调用数量不是独立重复数。"
             "不提供纯Harness分或五产品排名。", "",
             "| Episode | 写入公开载荷与最终文件匹配 | 可比写入分母 | 未知/被覆盖 | 真实错误文本对应error状态 | 可配对错误分母 |",
             "|---|---:|---:|---:|---:|---:|"]
    for episode in report["episodes"]:
        w = episode["metrics"]["final_write_payload_artifact_correspondence"]
        e = episode["metrics"]["explicit_error_status_projection"]
        package = public_root / episode["package"]
        import os
        relative = Path(os.path.relpath(package, destination.parent)).as_posix()
        lines.append(f"| [{episode['episode_id']}]({relative}) | {w['matching_instances']} | "
                     f"{w['comparable_final_instances']} | {w['unknown_instances']}/{w['superseded_instances']} | "
                     f"{e['explicit_error_instances']} | {e['paired_failure_instances']} |")
    lines += ["", f"已审计 {len(report['episodes'])} 个探索性episode；没有把多条工具调用合并成更多独立样本。", "",
              "写入分母：明确outputs目标的完成write，公开内容为字符串、请求/结果唯一对应、最终文件存在，"
              "且没有同目标的后续或重叠write/edit。按UTF-8编码公开请求内容，与最终文件原字节逐项计算SHA256。"
              "写入后有唯一配对且完成的write/edit，单列superseded并引用后续操作；后续/重叠操作失败、未完成或配对不明确，"
              "记unknown，不把工具报错当作未修改文件的证明。缺字段、目标无法对应或缺文件也记unknown。"
              "未重建shell、子会话或不可见修改，数值仅描述公开投射与最终快照是否一致，不证明最后一次实际写入。", "",
              "错误反馈分母：原生工具结果文本以Error:开头，且能用同一请求ID唯一对应先前实际请求。"
              "检查独立的status字段是否为error。无真实错误文本的成功调用不进入该分母；无法配对仍记unknown。", "",
              "置信高只针对可复核的字节一致或字段对应事实。差异不能自动归为Harness错误；日志截断、后续修改、"
              "路径映射或工具实现仍需检查。错误来源和后续恢复选择不能由这些指标定责。", "",
              "未覆盖的模型语义、Skill内容、状态持久化、实际执行参数、权限实现以及其他产品链路保持未知，不记0。"
              "本脚本目前只适配DSH公开可见事件；其余产品不因未适配而判失败。", "",
              "详细实例、公开事件行号、调用ID、载荷和文件哈希见harness-observations.json。"
              "manifest支持包内完整性，不单独证明来源真实性。", "",
              "复核命令：", "", "```powershell", "python -X utf8 scripts/audit_harness_observations.py", "```", ""]
    if report["excluded_packages"]:
        lines += ["未通过包级检查的目录：", ""]
        for item in report["excluded_packages"]:
            lines.append(f"- {item['episode_id']}：{item['reason']}；未生成指标，不补零。")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-root", type=Path, default=ROOT / "public/pilots")
    parser.add_argument("--json-output", type=Path, default=ROOT / "reports/harness-observations.json")
    parser.add_argument("--markdown-output", type=Path, default=ROOT / "reports/harness-observations.md")
    options = parser.parse_args()
    public_root = options.public_root.resolve()
    approved_root = (ROOT / "public").resolve()
    if not public_root.is_relative_to(approved_root):
        raise ValueError("Audit reads only evidence under this repository's public directory")
    for output in (options.json_output.resolve(), options.markdown_output.resolve()):
        if not output.is_relative_to((ROOT / "reports").resolve()):
            raise ValueError("Derived report output must stay under reports/")
    episodes, excluded = [], []
    for package in sorted(public_root.glob("dsh-*")):
        if not package.is_dir():
            continue
        try:
            if not package.resolve().is_relative_to(public_root):
                raise ValueError("Public package symlink escapes selected public evidence root")
            episodes.append(audit_episode(package, public_root))
        except (ValueError, KeyError, FileNotFoundError, UnicodeDecodeError) as error:
            # No raw event data, private paths or credential values are printed.
            reason = str(error).replace(str(ROOT), "<repo>").replace(ROOT.as_posix(), "<repo>")
            excluded.append({"episode_id": package.name, "reason": reason, "verdict": "unknown"})
    report = {
        "schema": "harness-boundary-public-audit-v1", "generated_at": datetime.now(timezone.utc).isoformat(),
        "adapter": "dsh_public_visible_events_v1", "formal_sample_count": 0,
        "audited_exploratory_episode_count": len(episodes), "pure_harness_score": None,
        "episodes": episodes, "excluded_packages": excluded,
        "outside_adapter_scope": ["codex", "workbuddy", "yuanbao", "doubao"],
        "limitations": LIMITATIONS, "auditor_sha256": digest(Path(__file__).read_bytes()),
    }
    options.json_output.parent.mkdir(parents=True, exist_ok=True)
    options.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    options.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    options.markdown_output.write_text(render_markdown(report, options.markdown_output.resolve(), public_root), encoding="utf-8")
    print(json.dumps({"episodes_audited": len(episodes), "excluded_packages": len(excluded),
                      "pure_harness_score": None, "outputs": ["reports/harness-observations.json", "reports/harness-observations.md"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
