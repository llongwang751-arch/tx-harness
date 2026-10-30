"""Independent re-derivation of the three v3 validity guards.

This file deliberately does not import `harness_eval` or `evaluation_v3`, and it
does not read `supplements/grader-v3/rules.json`.  It re-implements each guard
from the frozen case contract and the published example bytes:

* CSV_STRICT              -> a hand-written RFC4180 state machine, not csv.reader
* T03_CHANGELOG_KEYS      -> the top-level key set of the frozen oracle file
* DECODED_FORBIDDEN_TEXT  -> one regex-free round-trip search over the re-serialised JSON

The comparison target is the guard verdict published for every synthetic
example.  A disagreement is a finding, not something to paper over.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "public/grader-audit-v3"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def csv_error(data: bytes):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        return f"undecodable bytes: {error}"
    quoted = False
    field_has_text = False
    index = 0
    while index < len(text):
        char = text[index]
        if quoted:
            if char == '"':
                if text[index + 1:index + 2] == '"':
                    index += 2
                    continue
                quoted = False
            index += 1
            continue
        if char == '"':
            if field_has_text:
                return "quote inside an unquoted field"
            quoted = True
            index += 1
            continue
        if char in ",\r\n":
            field_has_text = False
            if char == "\r" and text[index + 1:index + 2] == "\n":
                index += 1
            index += 1
            continue
        field_has_text = True
        index += 1
    return "unclosed quoted field" if quoted else None


def decoded_marker_hits(path: Path, markers):
    """Re-serialise the parsed JSON and search the decoded text once."""
    document = json.loads(path.read_text(encoding="utf-8"))
    flat = json.dumps(document, ensure_ascii=False)
    return sorted({marker for marker in markers if marker in flat})


def guard_verdicts(case_id, outputs: Path):
    case = load(f"cases/{case_id}/case.json")
    oracle = load(f"cases/{case_id}/oracle.json")
    verdicts = {}
    for check in case["checks"]:
        config = check["config"]
        target = config["path"]
        path = outputs / target
        if check["kind"] == "csv_rows":
            key = ("CSV_STRICT", target)
            if key in verdicts:
                continue
            verdicts[key] = (False, "missing file") if not path.exists() else \
                (csv_error(path.read_bytes()) is None,
                 csv_error(path.read_bytes()) or "strict state machine accepted")
        elif check["kind"] == "text_excludes" and target.endswith(".json"):
            key = ("DECODED_FORBIDDEN_TEXT", target)
            if key in verdicts:
                continue
            if not path.exists():
                verdicts[key] = (False, "missing file")
                continue
            hits = decoded_marker_hits(path, config["values"])
            verdicts[key] = (not hits,
                             "decoded strings contain no marker" if not hits
                             else "decoded marker(s): " + ", ".join(hits))
    if case_id == "T03":
        target = "change_log.json"
        path = outputs / target
        # The frozen answer keeps the two top-level sections apart; the prompt
        # requires them in one file.  Deriving the key set from the answer, not
        # from the rule file, is the independence this check claims.
        expected = set(oracle["changes"]) | set(oracle["unchanged"])
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            same = isinstance(data, dict) and set(data) == expected
            verdicts[("T03_CHANGELOG_KEYS", target)] = (
                same, "top-level keys equal the oracle key set" if same
                else "top-level keys differ from the oracle key set")
        else:
            verdicts[("T03_CHANGELOG_KEYS", target)] = (False, "missing file")
    return verdicts


def run():
    published = load("reports/grader-audit-v3.json")
    disagreements = []
    compared = 0
    examples = 0
    for example in published["examples"]:
        example_id = example["example_id"]
        outputs = EXAMPLES / example_id / "outputs"
        folder = EXAMPLES / example_id
        case_id = example["case_id"]
        if not folder.is_dir():
            continue
        examples += 1
        mine = guard_verdicts(case_id, outputs)
        for guard in example["validity_guards"]:
            key = (guard["rule_id"], guard["path"])
            compared += 1
            if key not in mine:
                disagreements.append({"example": example_id, "rule": key[0], "path": key[1],
                                      "published": guard["passed"], "independent": "not evaluated"})
                continue
            if mine[key][0] != guard["passed"]:
                disagreements.append({"example": example_id, "rule": key[0], "path": key[1],
                                      "published": guard["passed"], "independent": mine[key][0],
                                      "independent_reason": mine[key][1]})
        for key, value in mine.items():
            if not any(guard["rule_id"] == key[0] and guard["path"] == key[1]
                       for guard in example["validity_guards"]):
                disagreements.append({"example": example_id, "rule": key[0], "path": key[1],
                                      "published": "absent", "independent": value[0]})
    return {
        "schema": "tx-harness/independent-guard-check/v1",
        "method": "independent re-implementation outside harness_eval and evaluation_v3: "
                  "hand-written CSV state machine, oracle key-set comparison, single "
                  "re-serialisation search. Compares guard verdicts, not legacy check scores.",
        "examples": examples,
        "guard_verdicts_compared": compared,
        "disagreements": disagreements,
        "agrees": not disagreements,
        "limits": "Covers the 22 published synthetic examples only; not a proof over all CSV "
                  "dialects, all JSON encodings, or any product output.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", help="write the canonical result to this repo-relative path")
    args = parser.parse_args()
    result = run()
    text = canonical(result)
    if args.write:
        (ROOT / args.write).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / args.write).write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.write(text)
    return 0 if result["agrees"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
