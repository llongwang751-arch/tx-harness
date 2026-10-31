"""The ledger must refuse cleanly, not merely look tidy.

Every rejection below is planted by the test itself: one changed output byte, a
swapped prompt, a contaminated run, an unknown verdict carrying a score, and a
duplicated run id.  If a gate stops rejecting one of them, this file fails.
"""
import copy
import json
import unittest

from scripts import independent_check
from scripts import ledger
from scripts import ledger_sources as sources


def clone(value):
    return json.loads(json.dumps(value))


class LedgerRecordChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = sources.build_runs()
        cls.by_id = {record["run_id"]: record for record in cls.records}

    def audit(self, records):
        report = ledger.Audit()
        ledger.check_records(report, records)
        return report.problems

    def test_every_run_carries_the_ten_mandated_fields(self):
        for record in self.records:
            with self.subTest(run=record["run_id"]):
                for field in ("run_id", "task", "product", "model", "tools", "permissions",
                              "skill_state", "timing", "evidence", "verdict"):
                    self.assertIn(field, record)
                self.assertEqual(len(record["task"]["case_sha256"]), 64)
                self.assertEqual(len(record["task"]["prompt_sha256"]), 64)

    def test_unknown_fields_always_carry_a_reason(self):
        for record in self.records:
            if record["model"]["label"] in (None, "", "unknown"):
                self.assertTrue(record["model"]["reason"], record["run_id"])
            if record["tools"]["state"] == "unknown":
                self.assertTrue(record["tools"]["reason"], record["run_id"])
            if record["timing"]["started_at"] is None:
                self.assertTrue(record["timing"]["reason"], record["run_id"])

    def test_duplicate_run_id_is_rejected(self):
        records = clone(self.records[:2])
        records[1]["run_id"] = records[0]["run_id"]
        self.assertTrue(any("duplicate run id" in problem for problem in self.audit(records)))

    def test_unknown_verdict_may_not_carry_a_score(self):
        records = clone(self.records)
        target = next(record for record in records if record["track"] == "adapter_calibration")
        target["verdict"] = {"state": "unknown", "reason": "planted", "objective_score": 42,
                             "objective_max": 60, "score_for_aggregate": 42}
        problems = self.audit(records)
        self.assertTrue(any("unknown verdict carries a score" in problem for problem in problems))

    def test_planted_output_byte_change_fails_the_evidence_gate(self):
        record = clone(self.by_id["codex-T01-r1-attempt02"])
        record["evidence"]["outputs"][0]["matches_graded"] = False
        record["gates"] = sources.run_gates(record)
        self.assertFalse(record["gates"]["evidence_valid"])
        self.assertFalse(sources.table_eligible(record))

    def test_swapped_prompt_fails_the_prompt_gate(self):
        record = clone(self.by_id["codex-T02-r1-attempt01"])
        record["prompt_validity"] = {"ok": False, "basis": ["planted: prompt does not match"]}
        record["gates"] = sources.run_gates(record)
        self.assertFalse(record["gates"]["prompt_valid"])
        self.assertFalse(sources.table_eligible(record))

    def test_contaminated_run_fails_the_contamination_gate(self):
        record = clone(self.by_id["doubao-T02-desktop-r1"])
        record["evidence"]["contamination"] = {"state": "suspected", "basis": ["planted"]}
        record["gates"] = sources.run_gates(record)
        self.assertFalse(record["gates"]["uncontaminated"])
        self.assertFalse(sources.table_eligible(record))

    def test_formal_table_cannot_hold_an_ineligible_row(self):
        records = clone(self.records)
        target = next(record for record in records
                      if record["track"] == "formal_product_end_to_end")
        target["evidence"]["contamination"] = {"state": "suspected", "basis": ["planted"]}
        target["gates"] = sources.run_gates(target)
        table = sources.build_table(records)
        report = ledger.Audit()
        ledger.check_table(report, records, table)
        self.assertTrue(any("ineligible run" in problem for problem in report.problems))


class LedgerAggregation(unittest.TestCase):
    def test_unknown_verdict_leaves_numerator_and_denominator(self):
        records = sources.build_runs()
        table = sources.build_table(records)
        for product in table["products"]:
            with self.subTest(product=product["product_id"]):
                self.assertEqual(product["pass"] + product["fail"], product["scored"])
                self.assertEqual(product["scored"] + product["unknown"]
                                 + product["excluded_by_gate"], product["runs"])
                self.assertIsNone(product["ranking"])
        self.assertIsNone(table["ranking"])
        self.assertTrue(table["ranking_withheld_because"])

    def test_six_accounts_are_not_added_together(self):
        records = sources.build_runs()
        accounts = sources.build_accounts(records)
        self.assertEqual(set(accounts) - {"_rules"}, set(sources.ACCOUNTS))
        self.assertNotIn("total", accounts)
        self.assertEqual(accounts["bare_model_probe"]["entries"], 0)
        self.assertTrue(accounts["bare_model_probe"]["stop_condition"])
        self.assertEqual(accounts["interface_preflight"]["tasks_counted"], 0)

    def test_account_numbers_match_their_frozen_artifacts(self):
        records = sources.build_runs()
        accounts = sources.build_accounts(records)
        self.assertEqual(accounts["product_run"]["entries"], len(records))
        audit = sources.load("reports/grader-audit-v3.json")
        expected = {spec["pointer"]: spec["expected"]
                    for spec in accounts["grader_regression"]["items"]}
        self.assertEqual(expected["/counts/synthetic_examples"],
                         audit["counts"]["synthetic_examples"])
        self.assertEqual(expected["/counts/ablation_checks"], audit["counts"]["ablation_checks"])


class LedgerArtifacts(unittest.TestCase):
    def test_conclusions_have_five_parts_and_replay(self):
        for name in ("CL-01", "CL-02", "CL-03", "CL-04"):
            conclusion = sources.load(f"ledger/conclusions/{name}.json")
            with self.subTest(conclusion=name):
                for part in ledger.FIVE_PARTS:
                    self.assertTrue(conclusion[part], part)
                expected = conclusion["reproducible_experiment"]["expected_output_sha256"]
                self.assertEqual(ledger.experiment_hash(name), expected)

    def test_revision_archive_keeps_all_six_elements(self):
        index = sources.load("ledger/revisions/index.json")
        self.assertEqual(len(index["revisions"]), 3)
        for revision in index["revisions"]:
            with self.subTest(revision=revision["id"]):
                for key in ("before", "after", "positive_control", "near_miss", "ablation",
                            "independent_acceptance", "historical_recompute_impact"):
                    self.assertIn(key, revision)
                self.assertTrue(revision["near_miss"]["legacy_accepted"])
                self.assertFalse(revision["near_miss"]["v3_accepted"])
                self.assertTrue(revision["independent_acceptance"]["agrees"])
                self.assertEqual(revision["historical_recompute_impact"]["newly_rejected"], 0)

    def test_independent_reimplementation_agrees_with_published_guards(self):
        result = independent_check.run()
        self.assertTrue(result["agrees"], result["disagreements"])
        self.assertEqual(result["examples"], 22)

    def test_unknown_register_keeps_impact_next_and_stop(self):
        register = sources.load("ledger/unknowns.json")
        previous = sources.load("supplements/week2/unknowns.json")
        self.assertLessEqual({item["id"] for item in previous["items"]},
                             {item["id"] for item in register["items"]})
        for item in register["items"]:
            with self.subTest(item=item["id"]):
                self.assertFalse(item["scored"])
                self.assertEqual(item["denominator"], "excluded")
                for key in ("impact", "next_action", "stop_condition"):
                    self.assertTrue(item[key])

    def test_self_test_artifact_matches_its_own_totals(self):
        payload = sources.load("ledger/self-test.json")
        self.assertEqual(payload["total"], sum(item["tests"] for item in payload["modules"]))
        self.assertEqual(payload["errors"], 0)
        self.assertIsInstance(payload["failures"], int)

    def test_repeat_batch_is_counted_but_stays_out_of_the_five_product_summary(self):
        records = sources.build_runs()
        repeats = [record for record in records if record["track"] == "repeat_batch"]
        self.assertEqual(len(repeats), 8)
        for record in repeats:
            self.assertEqual(record["verdict"]["state"], "pass")
            self.assertEqual(record["verdict"]["score_for_aggregate"], 60.0)
        table = sources.build_table(records)
        self.assertEqual(len(table["repeat_rows"]), 8)
        self.assertEqual({row["case_id"] for row in table["repeat_rows"]},
                         {"T01", "T02", "T03", "T05"})
        for product in table["products"]:
            self.assertEqual(product["runs"], 5)

    def test_repeat_stability_separates_bytes_from_semantics(self):
        conclusion = sources.load("ledger/conclusions/CL-03.json")
        self.assertEqual(ledger.experiment_hash("CL-03"),
                         conclusion["reproducible_experiment"]["expected_output_sha256"])
        projection = ledger.reproduce_cl03()["tasks"]
        self.assertEqual(projection["T01"]["scores"], [60.0, 60.0, 60.0])
        self.assertFalse(projection["T01"]["byte_identical_across_three"]["exceptions.json"])
        self.assertTrue(projection["T01"]["semantic_identical_across_three"]["exceptions.json"])
        self.assertTrue(all(projection["T02"]["byte_identical_across_three"].values()))
        self.assertFalse(projection["T03"]["byte_identical_across_three"]["change_log.json"])
        self.assertTrue(projection["T03"]["semantic_identical_across_three"]["change_log.json"])
        # The one T05 failure is a single draw: two repeats scored full marks.
        self.assertEqual(projection["T05"]["scores"], [30.0, 60.0, 60.0])
        self.assertFalse(projection["T05"]["all_passed"])

    def test_single_t05_failure_has_a_verified_cause(self):
        projection = ledger.reproduce_cl04()
        self.assertEqual(projection["runs"]["r1"]["b001_net_cents"], 10200)
        self.assertEqual(projection["runs"]["r2"]["b001_net_cents"], 8200)
        self.assertFalse(projection["runs"]["r1"]["summary_equals_own_ledger"])
        self.assertTrue(projection["runs"]["r2"]["summary_equals_own_ledger"])
        self.assertTrue(projection["only_r1_differs"])

    def test_generated_files_match_their_sources(self):
        problems = []
        records = sources.build_runs()
        expected = {
            "ledger/runs.jsonl": b"".join(ledger.line(record) for record in records),
            "ledger/formal-table.json": sources.canonical(sources.build_table(records)),
        }
        for relative, data in expected.items():
            with self.subTest(file=relative):
                path = sources.ROOT / relative
                if not path.exists() or path.read_bytes() != data:
                    problems.append(relative)
        self.assertEqual(problems, [])


class LedgerGateCoverage(unittest.TestCase):
    """The three cases that broke the first version of the admission gate."""

    @classmethod
    def setUpClass(cls):
        cls.by_id = {record["run_id"]: record for record in sources.build_runs()}

    def test_crlf_submitted_prompt_is_accepted_after_normalisation(self):
        record = self.by_id["workbuddy-T01-desktop-r1"]
        self.assertTrue(record["prompt_validity"]["ok"])
        basis = " ".join(record["prompt_validity"]["basis"])
        self.assertIn("line-ending normalisation=True", basis)

    def test_registered_supplement_is_not_treated_as_a_tampered_input(self):
        record = self.by_id["workbuddy-T04-desktop-r1"]
        self.assertTrue(record["evidence"]["inputs"]["state"])
        basis = " ".join(record["evidence"]["inputs"]["basis"])
        self.assertIn("registered supplement", basis)

    def test_run_without_artifacts_can_still_be_uncontaminated(self):
        record = self.by_id["yuanbao-T03-desktop-r1"]
        self.assertEqual(record["evidence"]["outputs"], [])
        self.assertEqual(record["evidence"]["contamination"]["state"], "none")
        self.assertFalse(record["verdict"]["state"] == "pass")

    def test_scored_end_to_end_run_keeps_its_artifact_score(self):
        record = self.by_id["dsh-sdk-T05-r1"]
        self.assertEqual(record["verdict"]["state"], "fail")
        self.assertEqual(record["verdict"]["score_for_aggregate"], 30.0)


if __name__ == "__main__":
    unittest.main()
