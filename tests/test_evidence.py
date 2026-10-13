"""Evidence lifecycle regressions with temporary, explicitly synthetic runs."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from harness_eval import core
from harness_eval import __main__ as cli
from tests.test_evaluation import write_golden_outputs


START = "2020-01-01T00:00:00+00:00"
FINISH = "2020-01-01T00:01:00+00:00"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-evidence-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / "evaluation"
        self.root.mkdir()
        # A private copy keeps source edits by another agent out of the fixtures.
        for name in ("config", "cases", "docs", "harness_eval"):
            shutil.copytree(core.ROOT / name, self.root / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for module in (core, cli):
            patcher = patch.object(module, "ROOT", self.root)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.protocol = core.read_json(self.root / "config/protocol.json")
        self.runs = self.directory / "synthetic-runs"

    def call(self, command, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return command(SimpleNamespace(**kwargs))

    def prepare(self, product="codex", case="T01", replicate=1, version="synthetic-v1"):
        self.call(cli.command_prepare, product=product, case=case, replicate=replicate,
                  track="product_default", runs_dir=str(self.runs))
        run = self.runs / f"product_default-{product}-{case}-r{replicate}"
        meta = core.read_json(run / "meta.json")
        meta.update(operator="SYNTHETIC_UNIT_TEST_OPERATOR", surface="synthetic-local-fixture",
                    product_version=version, model="SYNTHETIC_TEST_MODEL",
                    skill_condition=self.protocol["skill_condition"],
                    recording_limitations="Synthetic fixture, never a product observation.")
        core.write_json(run / "meta.json", meta)
        return run

    def evidence(self, run, filename="synthetic-capture.txt"):
        relative = "evidence/" + filename
        (run / relative).write_text("SYNTHETIC_TEST_ONLY: no product was executed.\n", encoding="utf-8")
        return relative

    def event(self, run, kind, at, evidence=None):
        return cli.append_event(run, kind, "SYNTHETIC_TEST_ONLY: " + kind,
                                evidence or [self.evidence(run)], at=at)

    def fill_manual(self, run, finish_event):
        manual = core.read_json(run / "manual.json")
        for item in manual["dimensions"].values():
            item.update(grade=4, reason="Synthetic gate regression fixture only.",
                        event_ids=[finish_event["id"]], confidence="high",
                        confidence_basis="Synthetic evidence hash verified inside temporary directory.",
                        alternative_explanation="No real product behavior is claimed.",
                        attribution="unresolved", reviewer="SYNTHETIC_UNIT_TEST_REVIEWER")
        core.write_json(run / "manual.json", manual)

    def finish_run(self, run, status="completed", manual=True, golden=True, sealed=True):
        meta = core.read_json(run / "meta.json")
        if golden:
            write_golden_outputs(self.root / "cases" / meta["case_id"], run / "workspace/outputs")
        self.event(run, "start", START)
        if meta["case_id"] == "T04" and status == "completed":
            request = cli.append_event(
                run, "observation", "SYNTHETIC_TEST_ONLY: missing rates.json exchange rates requested.",
                [self.evidence(run, "synthetic-request.txt")],
                at="2020-01-01T00:00:30+00:00")
            self.call(cli.command_release, run=str(run), file="rates.json", mode="active",
                      request_event=request["id"], at="2020-01-01T00:00:31+00:00",
                      note="SYNTHETIC_TEST_ONLY: prescribed active release")
        finish = self.event(run, "finish", FINISH)
        self.call(cli.command_finalize, run=str(run), status=status, at=FINISH,
                  note="SYNTHETIC_TEST_ONLY: stopped fixture")
        if manual:
            self.fill_manual(run, finish)
        if sealed:
            self.call(cli.command_seal, run=str(run))
        return run

    def test_prepare_is_pending_and_does_not_leak_oracles(self):
        run = self.prepare()
        meta, events = core.validate_run(run, require_sealed=False)
        self.assertEqual(meta["status"], "pending")
        self.assertEqual(events, [])
        workspace_files = core.inventory(run / "workspace")
        self.assertTrue(workspace_files)
        self.assertTrue(all(name == "prompt.md" or name.startswith("inputs/")
                            for name in workspace_files))
        self.assertFalse((run / "workspace/oracle.json").exists())
        with self.assertRaises(ValueError):
            self.call(cli.command_seal, run=str(run))

    def test_empty_snapshot_cannot_bypass_preregistration(self):
        run = self.prepare()
        core.write_json(run / "evaluation_snapshot.json", {})
        with self.assertRaises(ValueError):
            core.validate_run(run, require_sealed=False)

    def test_snapshot_fingerprint_must_match_registered_files(self):
        run = self.prepare()
        meta = core.read_json(run / "meta.json")
        meta["config_fingerprint"] = "0" * 64
        core.write_json(run / "meta.json", meta)
        with self.assertRaises(ValueError):
            core.validate_run(run, require_sealed=False)

    def test_invalid_or_mismatched_run_id_is_rejected(self):
        run = self.prepare()
        meta = core.read_json(run / "meta.json")
        for bad_id in ("../../escape", "product_default-workbuddy-T01-r1", "arbitrary"):
            with self.subTest(run_id=bad_id):
                meta["run_id"] = bad_id
                core.write_json(run / "meta.json", meta)
                with self.assertRaises(ValueError):
                    core.validate_run(run, require_sealed=False)

    def test_modified_sealed_output_is_rejected(self):
        run = self.finish_run(self.prepare())
        core.validate_run(run)
        (run / "workspace/outputs/aggregate.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            core.validate_run(run)

    def test_missing_manual_evidence_keeps_total_null(self):
        run = self.finish_run(self.prepare(), manual=False)
        result = core.score_run(run)
        self.assertEqual(result["objective_score"], 60)
        self.assertIsNone(result["total_score"])
        self.assertFalse(result["eligible"])
        self.assertTrue(result["missing_evidence"])

    def test_unsupported_status_with_nonzero_artifacts_is_rejected(self):
        run = self.prepare()
        with self.assertRaises(ValueError):
            self.finish_run(run, status="unsupported")
            core.score_run(run)

    def test_event_time_cannot_move_backwards(self):
        run = self.prepare()
        self.event(run, "start", START)
        self.event(run, "tool_result", FINISH)
        with self.assertRaises(ValueError):
            self.event(run, "finish", "2020-01-01T00:00:30+00:00")

    def test_validate_rejects_a_rewritten_reversed_event_timeline(self):
        run = self.prepare()
        self.event(run, "start", START)
        self.event(run, "finish", FINISH)
        event_path = run / "events.jsonl"
        events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        events[1]["at"] = "2019-12-31T23:59:59+00:00"
        event_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            core.validate_run(run, require_sealed=False)

    def test_finish_timestamp_must_match_metadata(self):
        run = self.finish_run(self.prepare(), sealed=False)
        meta = core.read_json(run / "meta.json")
        meta.update(ended_at="2020-01-01T00:01:01+00:00", elapsed_seconds=61)
        core.write_json(run / "meta.json", meta)
        with self.assertRaises(ValueError):
            core.validate_run(run, require_sealed=False)

    def test_finalize_cannot_backdate_before_finish_event(self):
        run = self.prepare()
        self.event(run, "start", START)
        self.event(run, "finish", FINISH)
        with self.assertRaises(ValueError):
            self.call(cli.command_finalize, run=str(run), status="completed",
                      at="2020-01-01T00:00:30+00:00", note="SYNTHETIC_TEST_ONLY")

    def test_task_events_cannot_be_added_after_finalize(self):
        run = self.finish_run(self.prepare(), sealed=False)
        with self.assertRaises(ValueError):
            self.event(run, "tool_result", "2020-01-01T00:02:00+00:00")

    def test_excess_interventions_can_be_preserved_as_failed_without_total(self):
        run = self.prepare()
        write_golden_outputs(self.root / "cases/T01", run / "workspace/outputs")
        self.event(run, "start", START)
        for second in (10, 20, 30):
            self.event(run, "intervention", f"2020-01-01T00:00:{second}+00:00")
        finish = self.event(run, "finish", FINISH)
        self.call(cli.command_finalize, run=str(run), status="failed", at=FINISH,
                  note="SYNTHETIC_TEST_ONLY: preserve excess-intervention deviation")
        self.fill_manual(run, finish)
        self.call(cli.command_seal, run=str(run))
        result = core.score_run(run)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["total_score"])
        self.assertFalse(result["eligible"])

    def test_completed_status_cannot_hide_elapsed_time_over_budget(self):
        run = self.prepare()
        self.event(run, "start", START)
        self.event(run, "finish", "2020-01-01T00:20:01+00:00")
        with self.assertRaises(ValueError):
            self.call(cli.command_finalize, run=str(run), status="completed",
                      at="2020-01-01T00:20:01+00:00", note="SYNTHETIC_TEST_ONLY")

    def test_t04_passive_release_waits_until_120_seconds_and_only_once(self):
        run = self.prepare(case="T04")
        self.event(run, "start", START)
        release_args = dict(run=str(run), file="rates.json", mode="passive", request_event=None,
                            note="SYNTHETIC_TEST_ONLY: prescribed passive release")
        with self.assertRaises(ValueError):
            self.call(cli.command_release, at="2020-01-01T00:01:59+00:00", **release_args)
        self.assertFalse((run / "workspace/inputs/rates.json").exists())
        self.call(cli.command_release, at="2020-01-01T00:02:00+00:00", **release_args)
        meta, events = core.validate_run(run, require_sealed=False)
        self.assertEqual(meta["scheduled_interventions"], 1)
        self.assertEqual(meta["unscheduled_interventions"], 0)
        self.assertEqual(events[-1]["kind"], "scheduled_release")
        self.assertEqual(meta["released_files"]["rates.json"],
                         core.sha256(run / "workspace/inputs/rates.json"))
        receipt = core.read_json(run / "evidence/release-receipt.json")
        self.assertEqual(receipt["mode"], "passive")
        with self.assertRaises(ValueError):
            self.call(cli.command_release, at="2020-01-01T00:02:01+00:00", **release_args)

    def test_t04_active_release_requires_existing_request_evidence_in_window(self):
        run = self.prepare(case="T04")
        self.event(run, "start", START)
        request = cli.append_event(run, "observation", "SYNTHETIC_TEST_ONLY: request rates.json.",
                                   [], at="2020-01-01T00:00:30+00:00")
        release_args = dict(run=str(run), file="rates.json", mode="active",
                            note="SYNTHETIC_TEST_ONLY: active release")
        for event_id in ("E999", request["id"]):
            with self.subTest(request_event=event_id), self.assertRaises(ValueError):
                self.call(cli.command_release, request_event=event_id,
                          at="2020-01-01T00:00:31+00:00", **release_args)
        request = self.event(run, "observation", "2020-01-01T00:02:01+00:00")
        with self.assertRaises(ValueError):
            self.call(cli.command_release, request_event=request["id"],
                      at="2020-01-01T00:02:02+00:00", **release_args)
        self.assertFalse((run / "workspace/inputs/rates.json").exists())

    def test_t04_rejected_release_after_finish_has_no_side_effects(self):
        run = self.prepare(case="T04")
        self.event(run, "start", START)
        self.event(run, "finish", FINISH)
        original_meta = core.read_json(run / "meta.json")
        original_inputs = core.inventory(run / "workspace/inputs")
        with self.assertRaises(ValueError):
            self.call(cli.command_release, run=str(run), file="rates.json", mode="passive",
                      request_event=None, at="2020-01-01T00:02:00+00:00",
                      note="SYNTHETIC_TEST_ONLY: invalid post-finish release")
        self.assertEqual(core.read_json(run / "meta.json"), original_meta)
        self.assertEqual(core.inventory(run / "workspace/inputs"), original_inputs)

    def test_t04_rejected_backdated_release_has_no_side_effects(self):
        run = self.prepare(case="T04")
        self.event(run, "start", START)
        self.event(run, "observation", "2020-01-01T00:02:01+00:00")
        original_meta = core.read_json(run / "meta.json")
        original_inputs = core.inventory(run / "workspace/inputs")
        with self.assertRaises(ValueError):
            self.call(cli.command_release, run=str(run), file="rates.json", mode="passive",
                      request_event=None, at="2020-01-01T00:02:00+00:00",
                      note="SYNTHETIC_TEST_ONLY: invalid backdated release")
        self.assertEqual(core.read_json(run / "meta.json"), original_meta)
        self.assertEqual(core.inventory(run / "workspace/inputs"), original_inputs)

    def test_different_versions_produce_different_runtime_configs(self):
        first = self.finish_run(self.prepare(replicate=1, version="synthetic-v1"))
        second = self.finish_run(self.prepare(replicate=2, version="synthetic-v2"))
        first_score, second_score = core.score_run(first), core.score_run(second)
        self.assertTrue(first_score["eligible"], first_score["missing_evidence"])
        self.assertTrue(second_score["eligible"], second_score["missing_evidence"])
        self.assertNotEqual(first_score["runtime_config"], second_score["runtime_config"])

    def preregister_fixture(self):
        self.protocol["status"] = "preregistered"
        core.write_json(self.root / "config/protocol.json", self.protocol)

    def report(self):
        target = self.directory / "synthetic-summary.md"
        self.call(cli.command_report, runs_dir=str(self.runs), out=str(target))
        return core.read_json(target.with_suffix(".json"))

    def test_single_complete_product_cannot_publish_complete_matrix_mean(self):
        self.preregister_fixture()
        for case in self.protocol["case_ids"]:
            for replicate in range(1, self.protocol["replicates"] + 1):
                self.finish_run(self.prepare(case=case, replicate=replicate))
        summary = self.report()
        self.assertTrue(all(item["mean_score"] is None for item in summary["products"]))

    def test_full_matrix_with_version_change_does_not_publish_complete_means(self):
        self.preregister_fixture()
        for product in self.protocol["product_ids"]:
            for case in self.protocol["case_ids"]:
                for replicate in range(1, self.protocol["replicates"] + 1):
                    version = "synthetic-v2" if (product, case, replicate) == ("codex", "T01", 1) \
                        else "synthetic-v1"
                    self.finish_run(self.prepare(product=product, case=case,
                                                 replicate=replicate, version=version))
        summary = self.report()
        codex = next(item for item in summary["products"] if item["product_id"] == "codex")
        self.assertEqual(codex["runtime_configs"], 2)
        self.assertIsNone(codex["mean_score"])
        self.assertTrue(all(item["mean_score"] is None for item in summary["products"]))

    def test_complete_matrix_aggregation_uses_registered_slots_and_equal_case_weights(self):
        self.preregister_fixture()
        scored = {}
        # Stub the scoring layer here: this test isolates aggregation, while the
        # real prepare/finalize/seal/score lifecycle is exercised above.
        for product in self.protocol["product_ids"]:
            for case_index, case in enumerate(self.protocol["case_ids"], 1):
                for replicate in range(1, self.protocol["replicates"] + 1):
                    run_id = f"product_default-{product}-{case}-r{replicate}"
                    run = self.runs / run_id
                    run.mkdir(parents=True)
                    record = dict(run_id=run_id, product_id=product, case_id=case,
                                  replicate=replicate, track="product_default", status="completed",
                                  eligible=True, total_score=10 * case_index + replicate,
                                  objective_score=10 * case_index, all_checks_passed=True,
                                  runtime_config={"product_version": "SYNTHETIC_TEST_VERSION"})
                    core.write_json(run / "meta.json", record)
                    scored[run_id] = record
        with patch.object(cli, "score_run", side_effect=lambda run: dict(scored[run.name])):
            summary = self.report()
        self.assertEqual(len(summary["runs"]), 75)
        for item in summary["products"]:
            self.assertEqual(item["eligible"], 15)
            self.assertEqual(item["collected"], 15)
            self.assertEqual(item["planned"], 15)
            self.assertEqual(item["mean_score"], 32)

    def test_duplicate_slot_cannot_be_selected_for_report(self):
        run = self.finish_run(self.prepare())
        shutil.copytree(run, self.runs / "duplicate-slot")
        with self.assertRaises(ValueError):
            self.report()

    def test_export_requires_review_before_sealing(self):
        run = self.finish_run(self.prepare())
        with self.assertRaises(ValueError):
            self.call(cli.command_export, run=str(run), out=str(self.directory / "unreviewed-copy"))

    def test_reviewed_export_is_local_copy_with_unchanged_manifest(self):
        run = self.finish_run(self.prepare(), sealed=False)
        meta = core.read_json(run / "meta.json")
        meta["redaction_reviewed"] = True
        core.write_json(run / "meta.json", meta)
        self.call(cli.command_seal, run=str(run))
        destination = self.directory / "local-reviewed-copy" / run.name
        self.call(cli.command_export, run=str(run), out=str(destination))
        self.assertEqual(core.sha256(run / "manifest.json"), core.sha256(destination / "manifest.json"))
        core.validate_run(destination)


if __name__ == "__main__":
    unittest.main()
