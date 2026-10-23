"""Re-sealed counterexamples exercise judgments beyond inventory hashes."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.audit_controlled_adapter import audit_package, bind_registration, build


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "public/supplements/controlled-adapter-v1"
FIXTURE = json.loads((ROOT / "supplements/controlled-adapter-v1/fixture.json").read_text(encoding="utf-8"))
SUCCESS_ID = "CA12-codex-success"
ERROR_ID = "CA14-codex-error"


class ControlledAdapterAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def package(self, run_id=SUCCESS_ID):
        target = self.directory / run_id
        shutil.copytree(BASE / run_id, target)
        return target

    def load(self, folder, name):
        return json.loads((folder / name).read_text(encoding="utf-8"))

    def save(self, folder, name, value):
        (folder / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")

    def lines(self, folder, name):
        return [json.loads(line) for line in (folder / name).read_text(encoding="utf-8").splitlines()]

    def save_lines(self, folder, name, rows):
        (folder / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                                   encoding="utf-8", newline="\n")

    def reseal(self, folder):
        manifest = self.load(folder, "manifest.json")
        manifest["files"] = [{"path": path.relative_to(folder).as_posix(), "bytes": path.stat().st_size,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                             for path in sorted(folder.rglob("*")) if path.is_file()
                             and path.name != "manifest.json"]
        self.save(folder, "manifest.json", manifest)

    def assert_contract_rejected(self, folder):
        self.reseal(folder)
        result = audit_package(folder, FIXTURE)
        self.assertTrue(result["inventory_valid"], result)
        self.assertNotEqual(result["outcome"], "pass", result)
        self.assertTrue(result.get("failed_checks") or result["integrity_errors"] or result["missing_evidence"])
        return result

    def test_real_success_and_error_packages_pass_without_inferring_native_error_boolean(self):
        for run_id in (SUCCESS_ID, ERROR_ID, "CA11-dsh-error", "CA13-dsh-success"):
            with self.subTest(run_id=run_id):
                result = audit_package(BASE / run_id, FIXTURE)
                self.assertEqual(result["outcome"], "pass", result)
                self.assertIsNone(result["is_error_observations"]["native_is_error"])
                self.assertEqual(result["is_error_observations"]["native_source"], "not_exposed")
        self.assertEqual(audit_package(BASE / ERROR_ID, FIXTURE)["is_error_observations"]["native_status"], "failed")

    def test_changed_mcp_result_is_rejected_after_manifest_is_resealed(self):
        folder = self.package()
        rows = self.lines(folder, "mcp-events.jsonl")
        call = next(row for row in rows if row["request"]["method"] == "tools/call")
        payload = json.loads(call["response"]["result"]["content"][0]["text"])
        payload["bytes"] += 1
        call["response"]["result"]["content"][0]["text"] = json.dumps(payload)
        self.save_lines(folder, "mcp-events.jsonl", rows)
        self.assert_contract_rejected(folder)

    def test_wrong_endpoint_call_id_is_rejected_after_resealing(self):
        folder = self.package()
        rows = self.lines(folder, "model-events.jsonl")
        returned = next(row for row in rows if row["kind"] == "model_request" and row["sequence"] == 2)
        returned["tool_return_items"][0]["call_id"] = "call_wrong"
        self.save_lines(folder, "model-events.jsonl", rows)
        self.assert_contract_rejected(folder)

    def test_wrong_arguments_are_rejected_even_when_mcp_and_native_agree(self):
        folder = self.package()
        model = self.lines(folder, "model-events.jsonl")
        for row in model:
            if row["kind"] == "fixed_tool_request":
                row["arguments"]["text"] = "a plausible but unfrozen answer"
                row["arguments_sha256"] = hashlib.sha256(json.dumps(row["arguments"], ensure_ascii=False,
                                                         separators=(",", ":")).encode()).hexdigest()
        mcp = self.lines(folder, "mcp-events.jsonl")
        next(row for row in mcp if row["request"]["method"] == "tools/call")["request"]["params"]["arguments"]["text"] = "a plausible but unfrozen answer"
        native = self.lines(folder, "native-events.jsonl")
        next(row for row in native if row["kind"] == "tool_call")["arguments"]["text"] = "a plausible but unfrozen answer"
        self.save_lines(folder, "model-events.jsonl", model)
        self.save_lines(folder, "mcp-events.jsonl", mcp)
        self.save_lines(folder, "native-events.jsonl", native)
        self.assert_contract_rejected(folder)

    def test_unicode_artifact_change_is_rejected_even_with_updated_receipt_and_inventory(self):
        folder = self.package()
        artifact = folder / "collected/artifact.txt"
        changed = artifact.read_bytes().replace("😀".encode(), "😃".encode())
        self.assertEqual(len(changed), 125)
        artifact.write_bytes(changed)
        execution = self.load(folder, "execution.json")
        execution["artifact"].update(bytes=len(changed), sha256=hashlib.sha256(changed).hexdigest())
        self.save(folder, "execution.json", execution)
        self.assert_contract_rejected(folder)

    def test_error_arm_cannot_be_relabelled_as_success_by_tool_payload(self):
        folder = self.package(ERROR_ID)
        rows = self.lines(folder, "mcp-events.jsonl")
        call = next(row for row in rows if row["request"]["method"] == "tools/call")
        call["response"]["result"] = {"content": [{"type": "text", "text": json.dumps({
            "marker": "CONTROLLED_TOOL_V1", "mode": "success", "bytes": 125,
            "sha256": hashlib.sha256(FIXTURE["arguments"]["text"].encode()).hexdigest()})}]}
        self.save_lines(folder, "mcp-events.jsonl", rows)
        self.assert_contract_rejected(folder)

    def test_error_arm_rejects_hidden_delivery_file_even_with_no_artifact_receipt(self):
        folder = self.package(ERROR_ID)
        (folder / "collected").mkdir()
        (folder / "collected/hidden.bin").write_bytes(FIXTURE["arguments"]["text"].encode())
        self.assert_contract_rejected(folder)

    def test_duplicate_call_is_rejected_after_resealing(self):
        folder = self.package()
        rows = self.lines(folder, "mcp-events.jsonl")
        rows.append(copy.deepcopy(next(row for row in rows if row["request"]["method"] == "tools/call")))
        self.save_lines(folder, "mcp-events.jsonl", rows)
        self.assert_contract_rejected(folder)

    def test_missing_native_terminal_is_rejected_although_fixed_model_finished(self):
        folder = self.package()
        rows = [row for row in self.lines(folder, "native-events.jsonl") if row["kind"] != "terminal"]
        self.save_lines(folder, "native-events.jsonl", rows)
        self.assert_contract_rejected(folder)

    def test_false_admission_cannot_inflate_independent_task_count(self):
        folder = self.package("CA00-codex-calibration")
        execution = self.load(folder, "execution.json")
        execution["task_accepted"] = True
        self.save(folder, "execution.json", execution)
        self.reseal(folder)
        result = audit_package(folder, FIXTURE)
        self.assertTrue(result["inventory_valid"])
        self.assertEqual(result["independent_task_count"], 0, result)
        self.assertFalse(result["task_accepted"])
        self.assertEqual(result["outcome"], "unknown")

    def test_calibration_and_main_denominators_are_separate(self):
        report = build(ROOT)
        self.assertEqual(report["counts"]["all"]["attempts"], 9)
        self.assertEqual(report["counts"]["all"]["independent_tasks"], 7)
        self.assertEqual(report["counts"]["all"]["not_accepted_attempts"], 2)
        self.assertEqual(report["counts"]["main"]["independent_tasks"], 4)
        self.assertEqual(report["counts"]["main"]["passed_tasks"], 4)
        self.assertEqual(report["counts"]["calibration"]["attempts"], 5)
        self.assertEqual(report["counts"]["calibration"]["independent_tasks"], 3)
        self.assertEqual(report["counts"]["calibration"]["passed_tasks"], 2)
        self.assertEqual(report["counts"]["calibration"]["unknown_tasks"], 1)
        self.assertTrue(all(not package["integrity_errors"] for package in report["packages"]))

    def test_registration_binds_executable_shared_tool_arguments_and_historical_commit(self):
        folder = self.package()
        result = audit_package(folder, FIXTURE)
        bind_registration(ROOT, folder, result, FIXTURE)
        self.assertGreater(result["registration"]["historical_source_blobs_verified"], 0)
        original = self.load(folder, "execution.json")
        for field in ("executable_sha256", "shared_tool_sha256", "frozen_arguments_sha256", "registration_commit"):
            with self.subTest(field=field):
                altered = copy.deepcopy(original)
                altered[field] = "0" * (40 if field == "registration_commit" else 64)
                self.save(folder, "execution.json", altered)
                self.reseal(folder)
                self.assertTrue(audit_package(folder, FIXTURE)["inventory_valid"])
                with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                    bind_registration(ROOT, folder, {}, FIXTURE)
        self.save(folder, "execution.json", original)

    def test_registered_source_blob_bytes_are_checked_against_their_frozen_hash(self):
        folder = self.package()
        actual = subprocess.check_output

        def one_corrupted_historical_blob(command, *args, **kwargs):
            value = actual(command, *args, **kwargs)
            if command[:2] == ["git", "show"] and command[2].endswith(":scripts/controlled_probe_mcp.py"):
                return value + b"\n# corrupted registered source\n"
            return value

        with patch("scripts.audit_controlled_adapter.subprocess.check_output", side_effect=one_corrupted_historical_blob):
            with self.assertRaisesRegex(ValueError, "source hash"):
                bind_registration(ROOT, folder, {}, FIXTURE)


if __name__ == "__main__":
    unittest.main()
