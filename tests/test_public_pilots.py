"""Regression for scored product failure versus unscored collection diagnostics.

The failed receipt is copied from an actual published pilot into a temporary
directory. This test never executes a product or changes published evidence.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import verify_public_pilots as verifier


class PublicPilotTests(unittest.TestCase):
    def test_empty_product_failure_is_scored_but_diagnostic_is_not(self):
        source = verifier.ROOT / "public/pilots/doubao-T01-desktop-r1"
        metadata = json.loads((source / "metadata.json").read_bytes())
        self.assertTrue(verifier.reported_product_failure(metadata))
        with tempfile.TemporaryDirectory(prefix="public-pilot-regression-") as temporary:
            folder = Path(temporary)
            (folder / "outputs").mkdir()
            shutil.copyfile(source / "verification.json", folder / "verification.json")
            result = verifier.verify_task_result(folder, "T01", metadata)
            self.assertEqual(result["objective_score"], 0)
            self.assertEqual(len(result["checks"]), 8)
            self.assertTrue(all(not check["passed"] for check in result["checks"]))

            # Neither failure status nor a product flag alone establishes this category.
            for diagnostic in ({"execution_status": "failed", "infra_failure": "login"},
                               {"product_side_failure": True}, {}):
                with self.subTest(diagnostic=diagnostic):
                    self.assertIsNone(verifier.verify_task_result(folder, "T01", diagnostic))

            # A changed per-check receipt must fail even when its aggregate stays zero.
            recorded = json.loads((folder / "verification.json").read_bytes())
            recorded["checks"][0]["passed"] = True
            (folder / "verification.json").write_text(json.dumps(recorded), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Per-check result changed"):
                verifier.verify_task_result(folder, "T01", metadata)


if __name__ == "__main__":
    unittest.main()
