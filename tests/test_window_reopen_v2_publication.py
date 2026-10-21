"""Exercise plausible evidence-chain errors after package hashes are refreshed.

These are publication-verifier tests, never additional product executions.
"""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import verify_window_reopen_v2 as verifier


class WindowReopenV2PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.registered_at = verifier.registered_protocol()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.copy_run('R01-reopen')

    def copy_run(self, name):
        destination = self.root / name
        shutil.copytree(verifier.BASE / name, destination)
        return destination

    def read(self, relative, run=None):
        return verifier.read((run or self.run) / relative)

    def write(self, relative, value, run=None):
        path = (run or self.run) / relative
        if relative.endswith('.jsonl'):
            path.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in value), encoding='utf-8')
        else:
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    def refresh_manifest(self, run=None):
        directory = run or self.run
        manifest = self.read('manifest.json', directory)
        manifest['files'] = {
            p.relative_to(directory).as_posix(): {'bytes': p.stat().st_size, 'sha256': verifier.digest(p)}
            for p in sorted(directory.rglob('*')) if p.is_file() and p != directory / 'manifest.json'}
        self.write('manifest.json', manifest, directory)

    def rejected(self, reason, run=None):
        directory = run or self.run
        self.refresh_manifest(directory)
        with self.assertRaisesRegex(AssertionError, reason):
            verifier.verify_run(directory, self.protocol, self.registered_at)

    def change_scene(self, original, transform):
        public = self.read('scene-index.json')[original]
        data = self.read(public)
        transform(data)
        self.write(public, data)

    def test_registered_pair_passes_full_semantic_review(self):
        reopened = verifier.verify_run(self.run, self.protocol, self.registered_at)
        control = verifier.verify_run(self.copy_run('R02-control'), self.protocol, self.registered_at)
        self.assertEqual((reopened['primary_outcome'], control['primary_outcome']), ('pass', 'pass'))
        self.assertLess(verifier.instant(reopened['ended_at']), verifier.instant(control['started_at']))

    def test_unlisted_artifact_rejected(self):
        (self.run / 'forgotten-original.txt').write_bytes(b'unlisted')
        with self.assertRaisesRegex(AssertionError, 'inventory differs'):
            verifier.verify_run(self.run, self.protocol, self.registered_at)

    def test_retrieval_cannot_be_relabelled_shell_copy(self):
        receipts = self.read('ui-retrieval.json')
        receipts[2]['method'] = 'shell_copy'
        self.write('ui-retrieval.json', receipts)
        self.rejected('direct-retrieval check failed')

    def test_after_retrieval_cannot_reuse_before_scene(self):
        receipts = self.read('ui-retrieval.json')
        receipts[2]['source_scene'] = receipts[0]['source_scene']
        self.write('ui-retrieval.json', receipts)
        self.rejected('After retrieval outside')

    def test_save_dialog_must_name_the_acquired_run_destination(self):
        scene = self.read('ui-retrieval.json')[2]['destination_scene']
        def wrong_run(data):
            for line in data['lines']:
                line['text'] = line['text'].replace('R01-reopen', 'another-task')
        self.change_scene(scene, wrong_run)
        self.rejected('Save As dialog does not name')

    def test_original_message_must_retain_every_frozen_prompt_line(self):
        scene = self.read('ui-retrieval.json')[2]['source_scene']
        def missing_constraint(data):
            data['lines'] = [line for line in data['lines']
                             if '不需要联网、修改其他资料' not in line['text']]
        self.change_scene(scene, missing_constraint)
        self.rejected('Original frozen prompt line missing')

    def test_close_launch_before_last_empty_inventory_rejected(self):
        proof = self.read('close-proof.json')
        proof['launch_at'] = proof['observations'][-2]['at']
        self.write('close-proof.json', proof)
        self.rejected('close-intervention check failed')

    def test_same_task_flag_alone_cannot_replace_title_evidence(self):
        proof = self.read('close-proof.json')
        title = self.read('primary.json')['task_title']
        def wrong_title(data):
            for row in data['lines']:
                row['text'] = row['text'].replace(title, '另一项无关任务')
        self.change_scene(proof['identity_scene'], wrong_title)
        self.rejected('Task title missing')

    def test_unrelated_window_cannot_serve_as_workbuddy_inventory(self):
        proof = self.read('close-proof.json')
        proof['before_windows'][0]['app'] = 'process:E:\\another\\Other.exe'
        self.write('close-proof.json', proof)
        self.rejected('Close inventories do not identify WorkBuddy')

    def test_custody_journal_cannot_repeat_a_receipt_even_with_matching_seal(self):
        rows = verifier.jsonl(self.run / 'collection.jsonl')
        rows.append(deepcopy(rows[-1]))
        seal = self.read('seal.json')
        seal['inventory'] = rows
        self.write('collection.jsonl', rows)
        self.write('seal.json', seal)
        self.rejected('exactly seven unique')

    def test_monotonic_clock_cannot_disagree_with_wall_clock(self):
        seal = self.read('seal.json')
        seal['elapsed_ms'] -= 2000
        self.write('seal.json', seal)
        self.rejected('Wall clock and monotonic elapsed')

    def test_ui_receipt_must_match_actual_custody_time(self):
        receipts = self.read('ui-retrieval.json')
        receipts[2]['elapsed_ms'] += 10
        self.write('ui-retrieval.json', receipts)
        self.rejected('UI receipt and custody journal disagree')

    def test_primary_observation_cannot_be_recorded_after_continuation(self):
        primary = self.read('primary.json')
        start = verifier.instant(self.read('execution.json')['started_at'])
        primary['at'] = self.read('continuation.json')['after_at']
        primary['elapsed_ms'] = (verifier.instant(primary['at'])-start).total_seconds()*1000
        self.write('primary.json', primary)
        self.rejected('Checkpoint/primary/continuation timing failed')

    def test_declared_delay_must_match_wall_time(self):
        continuation = self.read('continuation.json')
        continuation['delay_seconds'] = 175
        self.write('continuation.json', continuation)
        self.rejected('Checkpoint/primary/continuation timing failed')

    def test_model_message_during_primary_cannot_be_hidden_by_zero_counter(self):
        rows = verifier.jsonl(self.run / 'actions.jsonl')
        at = verifier.instant(self.read('checkpoint.json')['at'])+timedelta(seconds=1)
        rows.append({'at': at.isoformat(), 'label': 'recover-with-model', 'method': 'paste',
                     'args': ['请重新生成附件。'], 'result': 'returned'})
        rows.sort(key=lambda r: verifier.instant(r['at']))
        self.write('actions.jsonl', rows)
        self.rejected('Unexpected message/input operation during primary')

    def test_control_close_action_rejected_despite_window_kept_open_claim(self):
        control = self.copy_run('R02-control')
        rows = verifier.jsonl(control / 'actions.jsonl')
        at = verifier.instant(self.read('primary.json', control)['at'])+timedelta(seconds=1)
        rows.append({'at': at.isoformat(), 'label': 'unregistered-close', 'method': 'pressKey',
                     'args': ['alt+F4'], 'result': 'returned'})
        rows.sort(key=lambda r: verifier.instant(r['at']))
        self.write('actions.jsonl', rows, control)
        self.rejected('Control contains close action', control)

    def test_local_retrieval_cannot_upgrade_cloud_storage_to_pass(self):
        review = self.read('review.json')
        review['metrics']['attachment_cloud_storage']['status'] = 'pass'
        self.write('review.json', review)
        self.rejected('Review status overstates evidence')

    def test_judge_is_recomputed_instead_of_trusting_pass_json(self):
        path = self.run / 'outputs/receipt.json'
        # All recorded counts/hashes can be refreshed; a duplicated receipt key still violates the frozen contract.
        path.write_text('{"stage":"B","stage":"B","source":"probe.txt","bytes":137,"sha256":"'+
                        self.protocol['files'][verifier.PROBE]['sha256']+'"}\n', encoding='utf-8')
        self.rejected('Frozen byte/receipt judgment differs')

    def test_excerpt_cannot_alias_another_private_source_capture(self):
        source = self.read('ui-retrieval.json')[2]['source_scene']
        self.change_scene(source, lambda data: data.update(source_capture='captures/unrelated.ax.txt'))
        self.rejected('AX excerpt source metadata')


if __name__ == '__main__':
    unittest.main()
