"""Offline export/audit tests over completed fixture logs; no GUI is read."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_controlled_workbuddy import audit_package, export_private, read, save, sha


ROOT = Path(__file__).resolve().parents[1]
RUNS = ((1, "WBC00-workbuddy-calibration"), (2, "WBC01-workbuddy-calibration"),
        (3, "WBC02-workbuddy-calibration"))


class WorkBuddyAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def export(self, version=2, run_id="WBC01-workbuddy-calibration"):
        source = self.source_copy(version, run_id)
        destination = self.root / f"controlled-workbuddy-v{version}" / run_id
        export_private(source, destination, root=ROOT)
        return destination

    def source_copy(self, version=2, run_id="WBC01-workbuddy-calibration"):
        """Reconstruct synthetic producer logs from public reviewed bytes only."""
        import shutil
        source = self.root / "source" / f"controlled-workbuddy-v{version}" / run_id
        source.mkdir(parents=True, exist_ok=True)
        public = ROOT / f"public/supplements/controlled-workbuddy-v{version}" / run_id
        for name in ("execution.json", "ready.json", "model-events.jsonl", "gui-scene.json"):
            shutil.copyfile(public / name, source / name)
        rows = []
        for line in (public / "mcp-events.jsonl").read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            rows.append({"received_at": item["received_at"], "completed_at": item["completed_at"],
                         "mode": item["mode"], "request": {"jsonrpc": "2.0", "id": item["request_id"],
                         "method": item["method"], "params": {}},
                         "response": {"jsonrpc": "2.0", "id": item["response_id"], "result": {}}})
        (source / "mcp-events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        save(source / "stop.json", {"reason": "synthetic offline export test"})
        return source

    def reseal(self, folder):
        manifest = read(folder / "manifest.json")
        manifest["files"] = [{"path": path.relative_to(folder).as_posix(), "bytes": path.stat().st_size,
                              "sha256": sha(path.read_bytes())} for path in sorted(folder.rglob("*"))
                             if path.is_file() and path.name != "manifest.json"]
        save(folder / "manifest.json", manifest)

    def test_completed_calibrations_stay_unknown_with_independent_native_acceptance(self):
        for version, run_id in RUNS:
            with self.subTest(version=version):
                folder = self.export(version, run_id)
                result = audit_package(folder, root=ROOT)
                self.assertEqual(result["outcome"], "unknown", result)
                self.assertTrue(result["task_accepted"])
                self.assertEqual(result["independent_tasks"], 1)
                self.assertFalse(result["product_failure"])
                self.assertFalse(result["integrity_errors"], result)
                self.assertIsNone(result["native_cli_exit_code"])
                self.assertIsNot(result["native_terminal"]["normal"], True)
                self.assertEqual(result["actual_mcp_calls"], 0)
                self.assertEqual(result["auxiliary_requests"], 0 if version == 1 else 1)

    def test_v3_host_timeout_does_not_establish_a_native_terminal_or_discovery(self):
        folder = self.export(3, "WBC02-workbuddy-calibration")
        result = audit_package(folder, root=ROOT)
        self.assertEqual(result["independent_tasks"], 1)
        self.assertEqual(result["outcome"], "unknown")
        self.assertEqual(result["total_model_requests"], 4)
        self.assertEqual(result["auxiliary_requests"], 1)
        self.assertEqual(result["fixture_rejection_events"], 3)
        self.assertEqual(result["transport_error_events"], 3)
        self.assertEqual(result["discovery_calls"], 0)
        self.assertEqual(result["actual_mcp_calls"], 0)
        self.assertEqual(result["host_stop_basis"], "task_deadline_expired")
        self.assertTrue(result["host_deadline_expired"])
        self.assertIsNone(result["native_terminal"]["normal"])
        self.assertEqual(result["native_terminal"]["status"], "unknown")
        self.assertFalse(result["native_completion_observed"])
        self.assertFalse(result["checks"]["native_completion"])
        self.assertFalse(result["product_failure"])
        self.assertFalse(result["integrity_errors"], result)

    def test_submission_alone_cannot_be_counted_as_an_accepted_task(self):
        folder = self.export()
        (folder / "gui-scene.json").unlink()
        self.reseal(folder)
        result = audit_package(folder, root=ROOT)
        self.assertTrue(result["actual_submitted"])
        self.assertFalse(result["task_accepted"])
        self.assertEqual(result["independent_tasks"], 0)
        self.assertEqual(result["outcome"], "unknown")

    def test_setting_acceptance_true_without_actual_scene_excerpt_is_insufficient(self):
        folder = self.export()
        scene = read(folder / "gui-scene.json")
        scene["task_accepted"] = True
        scene["raw_source"]["lines"] = []
        save(folder / "gui-scene.json", scene)
        self.reseal(folder)
        self.assertEqual(audit_package(folder, root=ROOT)["independent_tasks"], 0)

    def test_export_drops_raw_context_headers_tool_outputs_and_nested_descriptions(self):
        source = self.source_copy()
        model = [json.loads(line) for line in (source / "model-events.jsonl").read_text(encoding="utf-8").splitlines()]
        model[0].update(messages="SECRET_SYSTEM_BODY_81", headers={"Authorization": "SECRET_TOKEN_22"},
                        tool_return_items=[{"content": "SECRET_TOOL_OUTPUT_55"}])
        model[0]["tool_metadata"] = [{"name": "ToolSearch", "schema_sha256": "0" * 64,
                                      "description": "SECRET_TOOL_DESCRIPTION_62"}]
        (source / "model-events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in model), encoding="utf-8")
        destination = self.root / "public-package"
        export_private(source, destination, root=ROOT)
        public = (destination / "model-events.jsonl").read_text(encoding="utf-8")
        for secret in ("SECRET_SYSTEM_BODY_81", "SECRET_TOKEN_22", "SECRET_TOOL_OUTPUT_55", "SECRET_TOOL_DESCRIPTION_62"):
            self.assertNotIn(secret, public)
        self.assertIn("source_event_sha256", public)
        self.assertIn("ToolSearch", public)

    def test_only_reviewed_fixed_rejection_literals_are_exported(self):
        source = self.source_copy(3, "WBC02-workbuddy-calibration")
        model = [json.loads(line) for line in (source / "model-events.jsonl").read_text(encoding="utf-8").splitlines()]
        model.append({"kind": "fixture_rejection", "reason": "SECRET_UPSTREAM_DATA_86"})
        (source / "model-events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in model), encoding="utf-8")
        destination = self.root / "reviewed-reasons"
        export_private(source, destination, root=ROOT)
        public = (destination / "model-events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("SECRET_UPSTREAM_DATA_86", public)
        self.assertIn("ToolSearch declaration cannot validate the fixed bridge arguments", public)

    def test_changed_registration_or_shared_tool_is_not_accepted_after_resealing(self):
        folder = self.export()
        execution = read(folder / "execution.json")
        execution["shared_tool_sha256"] = "0" * 64
        save(folder / "execution.json", execution)
        self.reseal(folder)
        result = audit_package(folder, root=ROOT)
        self.assertTrue(result["integrity_errors"])
        self.assertEqual(result["outcome"], "unknown")
        self.assertFalse(result["product_failure"])

    def test_existing_public_package_is_not_overwritten(self):
        folder = self.export()
        before = hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest()
        source = self.root / "source/controlled-workbuddy-v2/WBC01-workbuddy-calibration"
        with self.assertRaises(FileExistsError): export_private(source, folder, root=ROOT)
        self.assertEqual(hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(), before)


if __name__ == "__main__": unittest.main()
