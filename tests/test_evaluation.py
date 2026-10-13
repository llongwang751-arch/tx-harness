"""Artifact checker tests, without running any evaluated product.

Golden outputs are assembled from evaluator answers only inside TemporaryDirectory.
They verify the checker contract and are never product performance observations.
"""

from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness_eval import core


def write_golden_outputs(case_dir: Path, outputs: Path) -> None:
    """Assemble a synthetic passing artifact set for the registered checks."""
    case, oracle = core.load_case(case_dir)
    outputs.mkdir(parents=True, exist_ok=True)
    json_payloads = {}
    for check in case["checks"]:
        cfg = check["config"]
        path = core.inside(outputs, cfg["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        kind = check["kind"]
        if kind == "exact_json":
            json_payloads[cfg["path"]] = copy.deepcopy(oracle[cfg["oracle_key"]])
        elif kind == "json_fields":
            payload = json_payloads.setdefault(cfg["path"], {})
            expected = copy.deepcopy(oracle[cfg["oracle_key"]])
            for key, value in expected.items():
                if key in payload and not core.json_equal(payload[key], value):
                    raise AssertionError(f"Conflicting fixture fields: {cfg['path']}:{key}")
                payload[key] = value
        elif kind == "csv_rows":
            rows = oracle[cfg["oracle_key"]]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        elif kind == "bytes_equal":
            shutil.copyfile(core.inside(case_dir, cfg["reference"]), path)
        elif kind == "file_exists":
            if not path.exists():
                path.write_text("SYNTHETIC_TEST_ONLY\n", encoding="utf-8")
    for name, payload in json_payloads.items():
        core.write_json(core.inside(outputs, name), payload)
    for check in case["checks"]:
        cfg, kind = check["config"], check["kind"]
        path = core.inside(outputs, cfg["path"])
        if kind == "text_contains":
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            additions = [value for value in cfg["values"] if value not in old]
            path.write_text(old + "\n" + "\n".join(additions), encoding="utf-8")
        elif kind == "text_excludes" and not path.exists():
            path.write_text("SYNTHETIC_TEST_ONLY\n", encoding="utf-8")


def damage_substantive_output(case_dir: Path, outputs: Path) -> None:
    """Corrupt a checked business value or a protected byte, preserving files."""
    case, _ = core.load_case(case_dir)
    check = next(c for c in case["checks"] if c["kind"] in {"csv_rows", "bytes_equal"})
    path = core.inside(outputs, check["config"]["path"])
    if check["kind"] == "bytes_equal":
        path.write_bytes(path.read_bytes() + b"\nSYNTHETIC_UNAUTHORIZED_CHANGE")
        return
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers, rows = reader.fieldnames, list(reader)
    monetary = [name for name in headers if name.endswith("_cents")]
    field = monetary[-1] if monetary else next(
        name for name in reversed(headers) if name not in check["config"]["key_columns"])
    rows[0][field] = "999999999"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-checker-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_each_registered_case_accepts_golden_and_rejects_business_error(self):
        protocol = core.read_json(core.ROOT / "config/protocol.json")
        self.assertEqual(set(protocol["case_ids"]), {"T01", "T02", "T03", "T04", "T05"})
        for case_id in protocol["case_ids"]:
            with self.subTest(case=case_id):
                case_dir = core.ROOT / "cases" / case_id
                outputs = self.directory / case_id
                write_golden_outputs(case_dir, outputs)
                passing = core.evaluate(case_dir, outputs)
                self.assertEqual(passing["objective_score"], 60)
                self.assertTrue(passing["all_checks_passed"], passing["checks"])
                self.assertTrue(passing["all_required_outputs_present"])
                damage_substantive_output(case_dir, outputs)
                damaged = core.evaluate(case_dir, outputs)
                self.assertLess(damaged["objective_score"], passing["objective_score"])
                self.assertFalse(damaged["all_checks_passed"])

    def test_duplicate_json_keys_are_rejected(self):
        path = self.directory / "duplicate.json"
        path.write_text('{"approved_cents":1,"approved_cents":2}', encoding="utf-8")
        with self.assertRaises(ValueError):
            core.read_json(path)

    def test_nonfinite_json_constants_are_rejected(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                path = self.directory / "nonfinite.json"
                path.write_text('{"amount":' + constant + '}', encoding="utf-8")
                with self.assertRaises(ValueError):
                    core.read_json(path)

    def test_json_boolean_does_not_equal_integer(self):
        self.assertFalse(core.json_equal(True, 1))
        self.assertFalse(core.json_equal({"count": False}, {"count": 0}))
        path = self.directory / "answer.json"
        core.write_json(path, {"count": True})
        check = {"id": "type-check", "title": "integer count", "weight": 100,
                 "kind": "exact_json", "config": {"path": "answer.json", "oracle_key": "answer"}}
        result = core.check_artifact(check, self.directory, self.directory,
                                     {"answer": {"count": 1}})
        self.assertFalse(result["passed"])

    def test_duplicate_csv_primary_key_fails_even_if_values_are_correct(self):
        path = self.directory / "ledger.csv"
        path.write_text("id,amount\nA,10\nA,10\n", encoding="utf-8")
        check = {"id": "duplicate-csv", "title": "unique ledger", "weight": 100,
                 "kind": "csv_rows", "config": {"path": "ledger.csv", "key_columns": ["id"],
                                                   "oracle_key": "ledger"}}
        result = core.check_artifact(check, self.directory, self.directory,
                                     {"ledger": [{"id": "A", "amount": "10"}]})
        self.assertFalse(result["passed"])
        self.assertIn("主键重复", result["reason"])

    def test_paths_cannot_escape_output_directory(self):
        for relative in ("../outside.json", "nested/../../outside.json",
                         str(self.directory.parent / "outside.json")):
            with self.subTest(path=relative), self.assertRaises(ValueError):
                core.inside(self.directory, relative)

    def test_missing_required_output_loses_points(self):
        case_dir = core.ROOT / "cases/T01"
        outputs = self.directory / "outputs"
        write_golden_outputs(case_dir, outputs)
        (outputs / "order_ledger.csv").unlink()
        result = core.evaluate(case_dir, outputs)
        self.assertFalse(result["all_required_outputs_present"])
        self.assertFalse(result["all_checks_passed"])
        self.assertLess(result["objective_score"], 60)


if __name__ == "__main__":
    unittest.main()
