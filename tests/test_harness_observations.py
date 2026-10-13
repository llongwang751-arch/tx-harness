"""Synthetic audit fixtures test exclusions, not product performance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/audit_harness_observations.py"
SPEC = importlib.util.spec_from_file_location("public_boundary_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class PublicBoundaryAuditTests(unittest.TestCase):
    def audit(self, later_events, final_content, earlier_events=(), intermediate_events=()):
        with tempfile.TemporaryDirectory() as directory:
            public_root = Path(directory)
            package = public_root / "dsh-synthetic"
            (package / "outputs").mkdir(parents=True)
            (package / "outputs/note.md").write_bytes(final_content.encode("utf-8"))
            metadata = {"case_id": "synthetic", "track": "pilot", "surface": "fixture"}
            (package / "run-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            events = list(earlier_events) + [
                {"type": "tool_call", "tool": "write", "callId": "first",
                 "input": {"file_path": "outputs/note.md", "content": "old"}},
            ] + list(intermediate_events) + [
                {"type": "tool_result", "callId": "first", "status": "completed", "result": "OK"},
            ] + later_events
            rows = [{"received_at": None, "source_stdout_line": n, "event": e}
                    for n, e in enumerate(events, 1)]
            (package / "visible-events.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            manifest = {file.relative_to(package).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                        for file in package.rglob("*") if file.is_file()}
            (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            return AUDIT.audit_episode(package, public_root)["metrics"]["final_write_payload_artifact_correspondence"]

    @staticmethod
    def edit_call():
        return {"type": "tool_call", "tool": "edit", "callId": "edit",
                "input": {"file_path": "outputs/note.md", "old_string": "old", "new_string": "new"}}

    def test_completed_edit_excludes_earlier_write(self):
        metric = self.audit([self.edit_call(), {"type": "tool_result", "callId": "edit",
                                               "status": "completed", "result": "OK"}], "new")
        self.assertEqual(metric["superseded_instances"], 1)
        self.assertEqual(metric["comparable_final_instances"], 0)
        self.assertEqual(metric["differing_instances"], 0)
        later = metric["instances"][0]["later_mutations"][0]
        self.assertEqual(later["request"]["public_line"], 3)
        self.assertEqual(later["result"]["public_line"], 4)

    def test_failed_edit_does_not_prove_file_unchanged(self):
        metric = self.audit([self.edit_call(), {"type": "tool_result", "callId": "edit",
                                               "status": "error", "result": "Error: interrupted"}], "old")
        self.assertEqual(metric["unknown_instances"], 1)
        self.assertEqual(metric["comparable_final_instances"], 0)

    def test_ambiguous_edit_results_remain_unknown(self):
        result = {"type": "tool_result", "callId": "edit", "status": "completed", "result": "OK"}
        metric = self.audit([self.edit_call(), result, result], "new")
        self.assertEqual(metric["unknown_instances"], 1)
        self.assertEqual(metric["superseded_instances"], 0)

    def test_unfinished_later_write_excludes_final_comparison(self):
        metric = self.audit([{"type": "tool_call", "tool": "write", "callId": "later",
                              "input": {"file_path": "outputs/note.md", "content": "new"}}], "old")
        self.assertEqual(metric["unknown_instances"], 2)
        self.assertEqual(metric["comparable_final_instances"], 0)

    def test_difference_is_an_observation_without_causal_verdict(self):
        metric = self.audit([], "different")
        self.assertEqual(metric["differing_instances"], 1)
        self.assertEqual(metric["instances"][0]["attribution"], "unresolved")

    def test_earlier_unfinished_edit_may_overlap_write(self):
        metric = self.audit([], "old", earlier_events=[self.edit_call()])
        self.assertEqual(metric["unknown_instances"], 1)
        self.assertEqual(metric["comparable_final_instances"], 0)

    def test_earlier_edit_finishing_during_write_remains_unknown(self):
        result = {"type": "tool_result", "callId": "edit", "status": "completed", "result": "OK"}
        metric = self.audit([], "old", earlier_events=[self.edit_call()], intermediate_events=[result])
        self.assertEqual(metric["unknown_instances"], 1)
        self.assertEqual(metric["superseded_instances"], 0)

    def test_edit_finished_before_write_does_not_exclude_write(self):
        result = {"type": "tool_result", "callId": "edit", "status": "completed", "result": "OK"}
        metric = self.audit([], "old", earlier_events=[self.edit_call(), result])
        self.assertEqual(metric["matching_instances"], 1)
        self.assertEqual(metric["unknown_instances"], 0)

    def test_uncertain_edit_after_completed_edit_remains_unknown(self):
        result = {"type": "tool_result", "callId": "edit", "status": "completed", "result": "OK"}
        pending = self.edit_call()
        pending["callId"] = "pending"
        metric = self.audit([self.edit_call(), result, pending], "new")
        self.assertEqual(metric["unknown_instances"], 1)
        self.assertEqual(metric["superseded_instances"], 0)

    def test_paths_are_not_guessed_from_outputs_substrings(self):
        for target in ("../outputs/note.md", "inputs/staging/outputs/note.md", "D:/unknown/outputs/note.md",
                       "outputs/../note.md", "outputs//note.md"):
            self.assertIsNone(AUDIT.output_relative(target))
        self.assertEqual(AUDIT.output_relative("outputs\\note.md"), "note.md")

    def test_windows_case_alias_edit_excludes_write(self):
        alias = self.edit_call()
        alias["input"]["file_path"] = "OUTPUTS/NOTE.MD"
        result = {"type": "tool_result", "callId": "edit", "status": "completed", "result": "OK"}
        metric = self.audit([alias, result], "new")
        self.assertEqual(metric["superseded_instances"], 1)
        self.assertEqual(metric["comparable_final_instances"], 0)


if __name__ == "__main__":
    unittest.main()
