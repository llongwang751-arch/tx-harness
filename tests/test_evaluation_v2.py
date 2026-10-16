"""Diagnostic/provenance regression tests; never launch evaluated products."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts import analyze_evaluation_v2 as analysis


class SandboxTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="evaluation-v2-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = analysis.Sources(self.root)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


class FieldDiagnosticsTests(SandboxTestCase):
    def test_missing_null_boolean_and_numeric_type_are_distinct(self):
        differences = analysis.json_differences({"null": None, "count": True, "float": 1.0},
                                               {"null": None, "absent": 0, "count": 1, "float": 1})
        self.assertEqual(len(differences), 3)
        missing = next(d for d in differences if d["kind"] == "missing_field")
        self.assertFalse(missing["actual_present"])
        self.assertIsNone(missing["actual"])
        self.assertEqual(missing["expected"], 0)
        self.assertEqual(sum(d["kind"] == "type_mismatch" for d in differences), 2)

    def test_subset_is_top_level_only_and_array_order_is_not_ignored(self):
        self.assertEqual(analysis.json_differences({"x": 1, "extra": 2}, {"x": 1}, subset=True), [])
        differences = analysis.json_differences({"nested": {"x": 1, "extra": 2}},
                                               {"nested": {"x": 1}}, subset=True)
        self.assertEqual(differences[0]["kind"], "extra_field")
        ordered = analysis.json_differences(["B", "A"], ["A", "B"])
        self.assertEqual([d["kind"] for d in ordered], ["array_order"])

    def test_csv_uses_primary_keys_and_retains_duplicate_ambiguity(self):
        expected = [{"id": "A", "amount": "10"}, {"id": "B", "amount": "20"}]
        path = self.write("public/pilots/test/outputs/ledger.csv", "amount,id\n20,B\n10,A\n")
        self.assertEqual(analysis.csv_differences(path, ["id"], expected, "/ledger"), [])
        path.write_text("id,amount\nA,10\nA,999\n", encoding="utf-8")
        differences = analysis.csv_differences(path, ["id"], expected, "/ledger")
        self.assertEqual({d["kind"] for d in differences}, {"duplicate_primary_key", "missing_row"})
        duplicate = next(d for d in differences if d["kind"] == "duplicate_primary_key")
        self.assertEqual(duplicate["locator"]["csv_data_rows"], [1, 2])
        self.assertEqual(len(duplicate["actual"]), 2)

    def test_csv_value_pointer_uses_oracle_order_not_actual_row_order(self):
        path = self.write("public/pilots/test/outputs/ledger.csv", "id,amount\nB,21\nA,10\n")
        differences = analysis.csv_differences(path, ["id"],
                                              [{"id": "A", "amount": "10"}, {"id": "B", "amount": "20"}], "/ledger")
        self.assertEqual(differences[0]["expected_pointer"], "/ledger/1/amount")
        self.assertEqual(differences[0]["locator"], {"primary_key": {"id": "B"}, "csv_data_row": 1, "column": "amount"})

    def test_csv_duplicate_header_and_ragged_row_are_explicit(self):
        expected = [{"id": "A", "amount": "10"}]
        for content, kind in (("id,id\nA,A\n", "csv_columns"),
                              ("id,amount\nA\n", "csv_row_shape")):
            path = self.write("public/pilots/test/outputs/ledger.csv", content)
            self.assertEqual(analysis.csv_differences(path, ["id"], expected, "/ledger")[0]["kind"], kind)

    def test_missing_and_invalid_json_do_not_invent_zero_field_values(self):
        check = {"id": "T01-C02", "title": "summary", "kind": "json_fields", "weight": 20,
                 "config": {"path": "answer.json", "oracle_key": "answer"}}
        self.write("cases/T01/case.json", json.dumps({"checks": [check]}))
        self.write("cases/T01/oracle.json", '{"answer":{"count":10}}')
        missing = analysis.diagnose_check(self.sources, "public/pilots/test", "T01", check, {"answer": {"count": 10}})
        self.assertEqual(missing["status"], "missing_file")
        self.assertFalse(missing["differences"][0]["actual_present"])
        self.assertEqual(missing["differences"][0]["expected_source"]["json_pointer"], "/checks/0/config/path")
        self.write("public/pilots/test/outputs/answer.json", '{"count":10,"count":0}')
        invalid = analysis.diagnose_check(analysis.Sources(self.root), "public/pilots/test", "T01", check, {"answer": {"count": 10}})
        self.assertEqual(invalid["status"], "parse_error")
        self.assertFalse(invalid["differences"][0]["actual_present"])

    def test_sources_reject_private_and_escape_paths(self):
        for name in ("private/run/meta.json", "public/pilots/../../private/run.json", "../outside.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.sources.reference(name)


class DeadlineEvidenceTests(SandboxTestCase):
    def fixture(self, observed="2026-01-01T00:05:00+00:00"):
        base = "public/pilots/test"
        value = '{"count":10}'
        sha = analysis.digest(value.encode())
        self.write(base + "/outputs/answer.json", value)
        self.write(base + "/native-downloads/answer.json", value)
        artifact = {"public_native_file": "native-downloads/answer.json", "sha256": sha,
                    "source_projection": analysis.PRESERVATION_STATEMENT,
                    "download_available_observed_at": observed,
                    "save_action_at": "2026-01-01T00:03:00+00:00", "downloaded_at": None,
                    "outputs": [{"logical_path": "answer.json", "sha256": sha, "zip_member": None}]}
        metadata = {"started_at": "2026-01-01T00:00:00+00:00", "completion_observed_at": "2026-01-01T00:01:00+00:00", "status": "completed"}
        self.write(base + "/metadata.json", json.dumps(metadata))
        return base, artifact, metadata

    def timeline(self, base, artifact, metadata):
        self.write(base + "/download-receipts.json", json.dumps({"artifacts": [artifact]}))
        return analysis.timeline(analysis.Sources(self.root), {"base": base}, base + "/metadata.json", metadata, ["answer.json"], 60)

    def test_completed_and_final_hash_do_not_establish_cutoff_bytes(self):
        base, artifact, metadata = self.fixture()
        result = analysis.timeline(analysis.Sources(self.root), {"base": base}, base + "/metadata.json", metadata, ["answer.json"], 60)
        self.assertIsNone(result["strict_cutoff_score"])
        self.assertEqual(result["within_budget_obtained_originals"]["evidence_status"], "unknown")

    def test_budget_original_chain_is_separate_from_strict_cutoff(self):
        result = self.timeline(*self.fixture())
        self.assertEqual(result["within_budget_obtained_originals"]["historical_binary_score_for_obtained_originals"], 60)
        self.assertIsNone(result["strict_cutoff_score"])
        self.assertEqual(result["cutoff_evidence_status"], "unknown_no_independent_cutoff_snapshot")

    def test_late_presence_does_not_backdate_or_establish_cutoff_failure(self):
        base, artifact, metadata = self.fixture("2026-01-01T00:21:00+00:00")
        result = self.timeline(base, artifact, metadata)
        self.assertEqual(result["within_budget_obtained_originals"]["evidence_status"], "unknown")
        self.assertIsNone(result["strict_cutoff_score"])
        self.assertEqual(result["artifact_acquisition"][0]["times"]["save_action_at"]["seconds_after_submit"], 180)

    def test_observed_original_requires_preservation_and_matching_bytes(self):
        for damage in ("missing_statement", "hash_mismatch"):
            with self.subTest(damage=damage):
                base, artifact, metadata = self.fixture()
                if damage == "missing_statement":
                    del artifact["source_projection"]
                else:
                    artifact["sha256"] = "0" * 64
                result = self.timeline(base, artifact, metadata)
                self.assertEqual(result["within_budget_obtained_originals"]["evidence_status"], "unknown")


class PublishedReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analysis.build_report()

    def test_selected_scope_and_scores_are_unchanged(self):
        self.assertEqual(len(self.report["runs"]), 25)
        self.assertEqual(len({(r["product_id"], r["case_id"]) for r in self.report["runs"]}), 25)
        self.assertTrue(all(r["historical_objective"]["binary_recomparison_consistent"] for r in self.report["runs"]))
        self.assertTrue(all(r["new_capability_score"] is None for r in self.report["runs"]))
        self.assertTrue(all(r["timeline"]["strict_cutoff_score"] is None for r in self.report["runs"]))
        supported = [r for r in self.report["runs"] if r["timeline"]["within_budget_obtained_originals"]["evidence_status"] != "unknown"]
        self.assertEqual(len(supported), 6)

    def test_declaration_weight_is_explicit_and_not_business_score(self):
        for row in self.report["runs"]:
            groups = row["check_classification_old_weight_only"]
            self.assertEqual(sum(g["maximum_in_old_60"] for g in groups.values()), 60)
            if row["case_id"] == "T04":
                self.assertEqual(groups["缺失及恢复声明"]["maximum_in_old_60"], 18)
            if row["case_id"] == "T05":
                self.assertEqual(groups["来源审计及边界声明"]["maximum_in_old_60"], 21)

    def test_ordinary_reply_and_delivery_review_are_not_conflated(self):
        row = next(r for r in self.report["runs"] if r["run_id"] == "yuanbao-T03-desktop-r1")
        self.assertEqual(row["timeline"]["ordinary_terminal_observation"]["seconds_after_submit"], 42.204)
        self.assertEqual(row["timeline"]["later_delivery_review_observation"]["seconds_after_submit"], 150.272)
        self.assertEqual(row["error_counts_without_new_denominator"]["missing_files"], 5)

    def test_every_present_json_pointer_resolves_and_sources_are_public(self):
        cache = {}
        def walk(value):
            if isinstance(value, dict):
                if "path" in value and "sha256" in value and "json_pointer" in value:
                    self.assertNotIn("private", Path(value["path"]).parts)
                    if value["present"] and value["json_pointer"]:
                        name = value["path"]
                        if name.endswith(".json"):
                            if name not in cache:
                                cache[name] = analysis.core.read_json(analysis.ROOT / name)
                            data = cache[name]
                            for part in value["json_pointer"].split("/")[1:]:
                                part = part.replace("~1", "/").replace("~0", "~")
                                data = data[int(part)] if isinstance(data, list) else data[part]
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(self.report)

    def test_generated_report_bytes_are_reproducible(self):
        self.assertEqual(analysis.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
