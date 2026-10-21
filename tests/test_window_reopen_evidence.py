import copy
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.verify_window_reopen import check_custody, check_timing
from scripts.verify_week2 import product_manifest

ROOT = Path(__file__).resolve().parents[1]


class WindowReopenEvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.run = 'W02-window-reopen'
        source = ROOT / 'public/supplements/window-reopen-v1' / self.run
        for name in ('checkpoint.json', 'continuation.json', 'collection.jsonl'):
            shutil.copyfile(source / name, self.directory / name)
        shutil.copytree(source / 'collected', self.directory / 'collected')
        self.execution = json.loads((source / 'execution.json').read_text(encoding='utf-8'))
        self.seal = json.loads((source / 'seal.json').read_text(encoding='utf-8'))
        self.protocol = json.loads((ROOT / 'supplements/window-reopen-v1/protocol.json').read_text(encoding='utf-8'))
        self.start = datetime.fromisoformat(self.execution['started_at'])
        self.end = datetime.fromisoformat(self.seal['at'])

    def write_journal(self, rows):
        (self.directory / 'collection.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')

    def check_custody(self, seal):
        check_custody(self.directory, seal, self.run, self.start, self.end)

    def test_genuine_unknown_run_still_has_valid_artifact_custody(self):
        self.assertEqual(self.execution['validity'], 'unknown')
        self.check_custody(self.seal)
        check_timing(self.directory, self.execution, self.seal, self.protocol)

    def test_empty_seal_and_empty_journal_cannot_prove_delivery(self):
        seal = {**self.seal, 'inventory': []}
        self.write_journal([])
        with self.assertRaises(AssertionError):
            self.check_custody(seal)

    def test_missing_final_receipt_rejected_even_if_journal_matches(self):
        seal = copy.deepcopy(self.seal)
        seal['inventory'] = [r for r in seal['inventory'] if not r['collected'].endswith('/receipt.json')]
        self.write_journal(seal['inventory'])
        with self.assertRaises(AssertionError):
            self.check_custody(seal)

    def test_duplicate_acquisition_rejected(self):
        seal = copy.deepcopy(self.seal)
        seal['inventory'].append(seal['inventory'][0])
        self.write_journal(seal['inventory'])
        with self.assertRaises(AssertionError):
            self.check_custody(seal)

    def test_altered_collected_bytes_rejected(self):
        (self.directory / 'collected/stage-b/stage-b.txt').write_bytes(b'changed')
        with self.assertRaises(AssertionError):
            self.check_custody(self.seal)

    def test_declared_delay_cannot_override_actual_timestamps(self):
        path = self.directory / 'continuation.json'
        record = json.loads(path.read_text(encoding='utf-8'))
        record['before_at'] = '2026-10-21T16:41:31.509Z'
        record['after_at'] = '2026-10-21T16:41:31.660Z'
        record['delay_seconds'] = 120
        path.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaises(AssertionError):
            check_timing(self.directory, self.execution, self.seal, self.protocol)

    def test_new_namespace_counts_product_runs_but_not_synthetic_examples(self):
        self.assertTrue(product_manifest('public/supplements/window-reopen-v1/W01-control/manifest.json'))
        self.assertTrue(product_manifest('public/supplements/window-reopen-v2/R01-reopen/manifest.json'))
        self.assertFalse(product_manifest('public/supplements/window-reopen-v2/fixtures/manifest.json'))
        self.assertFalse(product_manifest('public/grader-audit-v3/N1/manifest.json'))
        self.assertFalse(product_manifest('public/supplements/window-reopen-v1/fixtures/manifest.json'))


if __name__ == '__main__':
    unittest.main()
