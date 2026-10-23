from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.request import urlopen

from scripts.serve_controlled_workbuddy import BASE, now, serve_run, verify_registration, wait_for_operator


ROOT = Path(__file__).resolve().parents[1]


class ControlledWorkBuddyHostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"; self.repo.mkdir()
        (self.repo / BASE).mkdir(parents=True)
        (self.repo / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/controlled_probe_mcp.py", self.repo / "scripts/controlled_probe_mcp.py")
        self.fixture = {"arguments": {"text": "保留原字节\r\n  trailing  \n", "destination": "artifact.txt"},
                        "terminal": "CONTROLLED_DONE"}
        self.write(self.repo / BASE / "fixture.json", self.fixture)
        files = {}
        for name in ("scripts/controlled_probe_mcp.py", BASE + "/fixture.json"):
            data = (self.repo / name).read_bytes()
            files[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        protocol = {"phase": "calibration", "timeout_seconds": 120, "files": files,
                    "runs": [{"run_id": "WB00-calibration", "product_id": "workbuddy", "mode": "success"}]}
        self.write(self.repo / BASE / "calibration.json", protocol)
        for args in (["init", "-q"], ["config", "user.name", "Offline test"],
                     ["config", "user.email", "offline@example.invalid"], ["config", "core.autocrlf", "false"],
                     ["add", "."], ["commit", "-qm", "Freeze test fixture"]):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        self.commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    def test_registered_current_bytes_and_historical_blob_must_both_match(self):
        verify_registration(self.repo, "WB00-calibration", "calibration", self.commit)
        source = self.repo / "scripts/controlled_probe_mcp.py"
        source.write_bytes(source.read_bytes() + b"\n# altered after registration\n")
        with self.assertRaisesRegex(ValueError, "supporting file changed"):
            verify_registration(self.repo, "WB00-calibration", "calibration", self.commit)
        # Altering the hash inventory too cannot replace the original protocol.
        protocol_path = self.repo / BASE / "calibration.json"
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        protocol["files"]["scripts/controlled_probe_mcp.py"] = {
            "bytes": source.stat().st_size, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        self.write(protocol_path, protocol)
        with self.assertRaisesRegex(ValueError, "registered git blob"):
            verify_registration(self.repo, "WB00-calibration", "calibration", self.commit)

    def test_unknown_or_escaping_run_never_creates_a_run(self):
        for run_id in ("../escape", "WB99-not-registered"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                serve_run(run_id, "calibration", self.commit, repo_root=self.repo,
                          work_root=self.root / "work", private_root=self.root / "evidence")
        self.assertFalse((self.root / "work").exists())

    def test_real_loopback_host_waits_for_stop_and_collects_exact_bytes(self):
        work, private = self.root / "work", self.root / "evidence"
        output, errors = [], []

        def launch():
            try:
                output.append(serve_run("WB00-calibration", "calibration", self.commit,
                                       repo_root=self.repo, work_root=work, private_root=private, poll_seconds=.01))
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=launch); thread.start()
        self.addCleanup(thread.join, 5)
        evidence = private / "WB00-calibration"
        limit = time.monotonic() + 5
        while not (evidence / "ready.json").exists() and time.monotonic() < limit:
            time.sleep(.01)
        ready = json.loads((evidence / "ready.json").read_text(encoding="utf-8"))
        self.assertEqual(ready["chat_url"], ready["base_url"] + "/chat/completions")
        self.assertTrue(ready["base_url"].startswith("http://127.0.0.1:"))
        with urlopen(ready["base_url"] + "/models", timeout=3) as response:
            self.assertEqual(json.load(response)["data"][0]["id"], "fixed-tool-v1")
        self.assertTrue(thread.is_alive())
        data = self.fixture["arguments"]["text"].encode("utf-8")
        (Path(ready["workspace"]) / "artifact.txt").write_bytes(data)
        self.write(evidence / "submission.json", {"at": now(), "actual_submitted": True,
                                                  "method": "native_computer_use"})
        self.write(evidence / "stop.json", {"reason": "offline operator test"})
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors, errors)
        result = output[0]
        self.assertTrue(result["actual_submitted"])
        self.assertEqual(result["stop_basis"], "operator_stop")
        self.assertEqual(result["artifact"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual((evidence / "collected/artifact.txt").read_bytes(), data)
        self.assertFalse(result["real_model_inference"])
        self.assertFalse(result["product_process_started_by_host"])
        with self.assertRaises(FileExistsError):
            serve_run("WB00-calibration", "calibration", self.commit, repo_root=self.repo,
                      work_root=work, private_root=private)

    def test_two_requests_do_not_end_host_and_budget_uses_actual_submission_time(self):
        evidence = self.root / "operator"; evidence.mkdir()
        wall = datetime(2026, 10, 24, tzinfo=timezone.utc)
        self.write(evidence / "submission.json", {"at": (wall - timedelta(seconds=25)).isoformat(),
                   "actual_submitted": True, "method": "native_computer_use"})
        clock = [0.0]

        def advance(_):
            clock[0] += 10

        result = wait_for_operator(evidence, (wall - timedelta(seconds=30)).isoformat(), lambda: 2,
                                   monotonic=lambda: clock[0], sleep=advance,
                                   current_time=lambda: wall.isoformat())
        self.assertEqual(clock[0], 100)
        self.assertEqual(result["stop_basis"], "task_deadline_expired")
        self.assertTrue(result["deadline_expired"])
        self.assertIsNotNone(result["submission"])

    def test_preparation_timeout_does_not_create_a_submission(self):
        evidence = self.root / "operator"; evidence.mkdir()
        clock = [0.0]

        def advance(_):
            clock[0] += 300

        result = wait_for_operator(evidence, now(), lambda: 0,
                                   monotonic=lambda: clock[0], sleep=advance)
        self.assertEqual(clock[0], 900)
        self.assertEqual(result["stop_basis"], "preparation_deadline_expired")
        self.assertIsNone(result["submission"])

    def test_stop_without_submission_stays_an_unsubmitted_preparation(self):
        evidence = self.root / "operator"; evidence.mkdir()
        self.write(evidence / "stop.json", {"reason": "configuration unavailable"})
        result = wait_for_operator(evidence, now(), lambda: 0)
        self.assertIsNone(result["submission"])
        self.assertEqual(result["stop_basis"], "operator_stop")

    def test_invalid_submission_is_not_accepted(self):
        evidence = self.root / "operator"; evidence.mkdir()
        self.write(evidence / "submission.json", {"at": now(), "actual_submitted": True,
                                                  "method": "shell_started_product"})
        with self.assertRaisesRegex(ValueError, "native Computer Use"):
            wait_for_operator(evidence, now(), lambda: 0)


if __name__ == "__main__":
    unittest.main()
