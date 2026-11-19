from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import behavior_preflight as gate
from scripts import behavior_codex_access as access
from scripts import run_codex_pilot


class BehaviorPreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.workspace = Path(tmp.name) / "workspace"
        self.case = gate.ROOT / "cases/T03-M"

    def stage(self, *, omit_inputs=False):
        (self.workspace / "outputs").mkdir(parents=True)
        shutil.copyfile(self.case / "prompt.md", self.workspace / "prompt.md")
        if not omit_inputs:
            shutil.copytree(self.case / "inputs", self.workspace / "inputs")

    def test_missing_inputs_stop_preparation(self):
        with self.assertRaisesRegex(ValueError, "missing inputs"):
            gate.stage_workspace(self.case, self.workspace, lambda: self.stage(omit_inputs=True))

    def test_prebuilt_workspace_never_invokes_preparation(self):
        self.workspace.mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            gate.stage_workspace(self.case, self.workspace, lambda: self.fail("prepare was invoked"))

    def test_input_digest_mismatch_stops_preparation(self):
        def altered():
            self.stage()
            (self.workspace / "inputs/catalog.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            gate.stage_workspace(self.case, self.workspace, altered)

    def test_real_readable_scoring_file_fails_access_gate(self):
        expected = gate.stage_workspace(self.case, self.workspace, self.stage)
        with self.assertRaisesRegex(ValueError, "scoring data is readable"):
            gate.check_access(self.workspace, expected, [self.case / "oracle.json"])

    def test_missing_protected_file_is_not_permission_denied(self):
        expected = gate.stage_workspace(self.case, self.workspace, self.stage)
        with self.assertRaisesRegex(ValueError, "denial was not established"):
            gate.check_access(self.workspace, expected, [self.case / "absent.json"])

    def test_launcher_rejects_before_locating_product_or_calling_prepare(self):
        with patch.object(run_codex_pilot, "native_codex") as find_product:
            with self.assertRaisesRegex(ValueError, "committed prospective"):
                run_codex_pilot.main(["--case", "T03-M", "--execute"])
            find_product.assert_not_called()

    def test_prepare_cli_rejects_prebuilt_run_without_a_delivery_hint(self):
        run = self.workspace.parent / "pilot-codex-T03-M-r1"
        (run / "workspace").mkdir(parents=True)
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "harness_eval",
                               "prepare", "--case", "T03-M", "--product", "codex",
                               "--track", "pilot", "--runs-dir", str(self.workspace.parent)],
                              cwd=gate.ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(proc.stdout)
        self.assertFalse((run / "meta.json").exists())

    def test_valid_prepare_cli_stages_exact_inputs_without_authorizing_delivery(self):
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "harness_eval",
                               "prepare", "--case", "T03-M", "--product", "codex",
                               "--track", "pilot", "--runs-dir", str(self.workspace.parent)],
                              cwd=gate.ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("未授权投递", proc.stdout.decode("utf-8"))
        folder = self.workspace.parent / "pilot-codex-T03-M-r1"
        meta = gate.read_json(folder / "meta.json")
        self.assertEqual(meta["participant_input_hashes"], gate.inventory(folder / "workspace"))

    def test_actual_launcher_cli_returns_nonzero(self):
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8",
                               "scripts/run_codex_pilot.py", "--case", "T03-M", "--execute"],
                              cwd=gate.ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"committed prospective", proc.stderr)

    def test_access_receipt_requires_all_denials_and_exact_input_bytes(self):
        expected = {"inputs/announcement.md": "0123456789"}
        observation = {"schema": "codex-access-check/v1", "input_sha256": expected,
                       "protected_open": {"oracle": "denied:80070005", "grader": "denied:80070005"}}
        access.validate_observation(observation, expected, {"oracle", "grader"})
        for invalid in ("readable", "FileNotFoundException", "denied:80004005"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                access.validate_observation({**observation, "protected_open": {
                    "oracle": "denied:80070005", "grader": invalid}}, expected, {"oracle", "grader"})
        with self.assertRaises(ValueError):
            access.validate_observation({**observation, "input_sha256": {}}, expected, {"oracle", "grader"})

    def test_valid_registration_stays_closed_without_independent_review(self):
        with patch.object(gate, "check_registration", return_value={"attempt": 1, "requested_model": None}), \
                patch.object(gate, "check_formal_readiness"), \
                patch.object(gate, "REVIEW", "reports/behavior-formal/no-review-fixture.json"), \
                patch.object(run_codex_pilot, "native_codex") as executable:
            with self.assertRaisesRegex(ValueError, "awaits the independent"):
                run_codex_pilot.main(["--case", "T03-M", "--track", "product_default", "--replicate", "2",
                                      "--registration-commit", "a" * 40, "--execute"])
            executable.assert_not_called()


if __name__ == "__main__":
    unittest.main()
