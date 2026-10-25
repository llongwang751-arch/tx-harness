"""Admission checks prevent GUI preflights and submitted-only attempts inflating totals."""
import unittest
from unittest.mock import patch

from scripts import verify_week2 as weekly


class WorkBuddyWeeklyAdmission(unittest.TestCase):
    name = 'public/supplements/controlled-workbuddy-v3/WBC02-workbuddy-calibration/manifest.json'

    def admitted(self, execution, scene):
        def read(path):
            return execution if path.name == 'execution.json' else scene
        with patch.object(weekly.core, 'read_json', side_effect=read):
            return weekly.product_manifest(self.name)

    def test_submit_without_native_acceptance_is_not_a_run(self):
        self.assertFalse(self.admitted({'actual_submitted': True}, {}))

    def test_normalized_native_acceptance_is_a_run_even_with_unknown_terminal(self):
        execution = {'run_id': 'WBC02-workbuddy-calibration', 'actual_submitted': True}
        scene = {'run_id': execution['run_id'], 'task_accepted': True,
                 'acceptance_basis': ['Native user bubble and endpoint requests'],
                 'native_terminal': {'normal': None}}
        self.assertTrue(self.admitted(execution, scene))

    def test_missing_or_different_native_admission_is_rejected(self):
        execution = {'run_id': 'WBC02-workbuddy-calibration', 'actual_submitted': True}
        for scene in ({'task_accepted': True, 'run_id': 'different-task', 'acceptance_basis': ['bubble']},
                      {'task_accepted': True, 'run_id': execution['run_id'], 'acceptance_basis': []}):
            with self.subTest(scene=scene), self.assertRaises(ValueError):
                self.admitted(execution, scene)

    def test_preflight_and_protocol_manifests_are_not_product_runs(self):
        for name in ('public/supplements/gui-controls-v1/manifest.json',
                     'public/supplements/controlled-workbuddy-v3/fixtures/manifest.json',
                     'public/grader-audit-v3/N1/manifest.json'):
            with self.subTest(name=name):
                self.assertFalse(weekly.product_manifest(name))


if __name__ == '__main__':
    unittest.main()
