"""Counterexamples and positive controls are grader tests, not product runs."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from evaluation_v3.grader import adjudicate
from harness_eval import core
from verify_week2 import count_executions, pointer


class GraderGuardTests(unittest.TestCase):
    def test_ablation_is_reversible_and_does_not_modify_the_artifacts(self):
        for example, case_id, responsible in [
            ('N6', 'T03', 'CSV_STRICT'), ('N7', 'T03', 'T03_CHANGELOG_KEYS'),
            ('N8', 'T05', 'DECODED_FORBIDDEN_TEXT'), ('N12', 'T05', 'DECODED_FORBIDDEN_TEXT')]:
            with self.subTest(example=example):
                path = ROOT / 'public/grader-audit-v3' / example / 'outputs'
                before = core.inventory(path)
                default = adjudicate(case_id, path)
                self.assertTrue(default['legacy_artifact_result']['all_checks_passed'])
                self.assertFalse(default['accepted'])
                self.assertIsNone(default['new_weighted_score'])
                self.assertTrue(adjudicate(case_id, path, disabled_rules=[responsible])['accepted'])
                self.assertEqual(core.inventory(path), before)

    def test_valid_serialization_choices_do_not_become_failures(self):
        for example, case_id in [('P1', 'T03'), ('P2', 'T03'), ('P3', 'T01'), ('P4', 'T03'), ('P5', 'T03')]:
            with self.subTest(example=example):
                self.assertTrue(adjudicate(case_id, ROOT / 'public/grader-audit-v3' / example / 'outputs')['accepted'])

    def test_t05_does_not_silently_acquire_a_ban_on_all_extra_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = Path(temporary) / 'outputs'
            shutil.copytree(ROOT / 'public/grader-audit-v3/G5/outputs', outputs)
            data = core.read_json(outputs / 'summary.json')
            data['note'] = {'nested': 'harmless ordinary annotation'}
            (outputs / 'summary.json').write_text(json.dumps(data), encoding='utf-8')
            self.assertTrue(adjudicate('T05', outputs)['accepted'])

    def test_unknown_case_or_ablation_rule_cannot_be_ignored(self):
        outputs = ROOT / 'public/grader-audit-v3/G3/outputs'
        with self.assertRaises(ValueError):
            adjudicate('../T03', outputs)
        with self.assertRaises(ValueError):
            adjudicate('T03', outputs, disabled_rules=['misspelled-rule'])


class WeeklyCountingTests(unittest.TestCase):
    def entry(self, name, validity='valid', outcome='pass'):
        return dict(run_id=name, native_submission_id=name, kind='product_execution',
                    actual_submitted=True, validity=validity, outcome=outcome)

    def test_valid_contains_known_product_failures_and_unknown_is_not_zero(self):
        data = count_executions([self.entry('a'), self.entry('b', outcome='fail'),
            self.entry('c', 'unknown', 'unknown'), self.entry('d', 'invalid', 'unknown')])
        self.assertEqual(data, {'independent_product_runs': 4, 'valid': 2,
            'passed': 1, 'failed': 1, 'unknown': 1, 'invalid': 1})

    def test_scoring_rows_and_duplicate_submissions_never_inflate_run_counts(self):
        row = self.entry('a')
        row['kind'] = 'synthetic_example'
        with self.assertRaises(ValueError):
            count_executions([row])
        with self.assertRaises(ValueError):
            count_executions([self.entry('a'), self.entry('a')])
        second = self.entry('b')
        second['native_submission_id'] = 'a'
        with self.assertRaises(ValueError):
            count_executions([self.entry('a'), second])

    def test_json_pointer_must_resolve_to_the_claimed_place(self):
        data = {'a/b': [{'~key': 42}]}
        self.assertEqual(pointer(data, '/a~1b/0/~0key'), 42)
        with self.assertRaises(KeyError):
            pointer(data, '/missing')


if __name__ == '__main__':
    unittest.main()
