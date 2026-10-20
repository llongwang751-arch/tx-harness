"""Public locators must remain inspectable without private files or a product."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_contract_evidence import audit_package, attachment_plan, contained_file, load_addenda
from contract_v2 import inventory, save, sha
from verify_contracts_v2 import delivery_denominators


class EvidenceLocatorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / 'S02-sample-r1-allow'
        self.package.mkdir()
        (self.package / 'artifact.json').write_bytes(b'{"result":true}\n')
        (self.package / 'visible-events.jsonl').write_text(json.dumps({
            'event_id': 'e1', 'source': {'file': 'unpublished-private-source.json'},
            'event': {'status': 'completed'}}) + '\n', encoding='utf-8')
        self.evidence = [{'event_id': 'e1'}, {'file': 'artifact.json',
                         'sha256': sha(self.package / 'artifact.json')}]

    def seal(self):
        save(self.package / 'review.json', {'observations': {'permission': {'evidence': self.evidence}}})
        files = inventory(self.package)
        files.pop('manifest.json', None)
        save(self.package / 'manifest.json', files)

    def test_public_event_and_file_resolve_without_private_source(self):
        self.seal()
        self.assertEqual([r['status'] for r in audit_package(self.package, {})],
                         ['resolved_locator', 'resolved_locator'])

    def test_dangling_file_is_rejected_even_if_no_hash_was_declared(self):
        self.evidence.append({'file': 'missing.json'})
        self.seal()
        with self.assertRaisesRegex(ValueError, 'Missing public evidence'):
            audit_package(self.package, {})

    def test_dangling_and_duplicate_event_ids_are_rejected(self):
        self.evidence[0]['event_id'] = 'absent'
        self.seal()
        with self.assertRaisesRegex(ValueError, 'Missing public event'):
            audit_package(self.package, {})
        with (self.package / 'visible-events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write('{"event_id":"e1"}\n')
        self.seal()
        with self.assertRaisesRegex(ValueError, 'Ambiguous event'):
            audit_package(self.package, {})

    def test_declared_hash_mismatch_and_postseal_tampering_are_rejected(self):
        self.evidence[1]['sha256'] = '0' * 64
        self.seal()
        with self.assertRaisesRegex(ValueError, 'Evidence hash mismatch'):
            audit_package(self.package, {})
        (self.package / 'artifact.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'manifest mismatch'):
            audit_package(self.package, {})

    def test_notes_do_not_become_machine_verified_events(self):
        self.evidence.extend(['e1 lines 1-3', {'sha256': '0' * 64}, {'note': 'manual only'}])
        self.seal()
        rows = audit_package(self.package, {})
        self.assertTrue(all(r['status'] == 'manual_note' for r in rows[-3:]))

    def test_paths_cannot_escape_on_windows_or_linux(self):
        for name in ['../secret', '/secret', 'C:/secret', 'a\\secret', 'a/../secret', './secret']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                contained_file(self.package, name)

    def test_addenda_require_existing_sealed_source_hash_and_unchanged_bytes(self):
        root = self.root / 'evidence-addenda'
        root.mkdir()
        (root / 'check.json').write_bytes(b'{"checked":true}\n')
        digest = sha(root / 'check.json')
        save(self.package / 'metadata.json', {'raw_records_sha256': {'check.json': digest}})
        entry = {'slot_id': self.package.name, 'referenced_file': 'check.json',
                 'public_file': 'check.json', 'sha256': digest,
                 'source_metadata_sha256': sha(self.package / 'metadata.json')}
        save(root / 'index.json', {'files': [entry]})
        addenda = load_addenda(self.root)
        self.evidence.append({'file': 'check.json', 'sha256': digest})
        self.seal()
        self.assertEqual(audit_package(self.package, addenda)[-1]['resolutions'][0]['kind'],
                         'anchored_addendum')
        (root / 'check.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Addendum bytes changed'):
            load_addenda(self.root)

    def test_addenda_cannot_claim_a_different_private_source_hash(self):
        root = self.root / 'evidence-addenda'
        root.mkdir()
        (root / 'check.json').write_bytes(b'{}')
        save(self.package / 'metadata.json', {'raw_records_sha256': {'check.json': '0' * 64}})
        save(root / 'index.json', {'files': [{'slot_id': self.package.name,
            'referenced_file': 'check.json', 'public_file': 'check.json',
            'sha256': sha(root / 'check.json'),
            'source_metadata_sha256': sha(self.package / 'metadata.json')}]})
        with self.assertRaisesRegex(ValueError, 'not anchored'):
            load_addenda(self.root)

    def test_export_never_publishes_unreviewed_private_attachments(self):
        review = {'observations': {'permission': {'evidence': [{'file': 'artifact.json'}]}}}
        with self.assertRaisesRegex(ValueError, 'explicit privacy review'):
            attachment_plan(self.package, review, set())
        review['public_attachment_files'] = ['artifact.json']
        self.assertIn('artifact.json', attachment_plan(self.package, review, set()))
        (self.package / 'artifact.json').write_text('C:/Users/sample/private.txt', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Potential private path'):
            attachment_plan(self.package, review, set())


class DeliveryDenominatorTests(unittest.TestCase):
    def test_absent_originals_and_unsealed_slots_are_never_byte_failures(self):
        rows = [dict(card='S01', product_id='sample', arm='normal', public_state='sealed',
            verification=dict(echo_present=True, echo_bytes_equal=False,
                              receipt_present=False, receipt_declaration_valid=False), end={}),
            dict(card='S01', product_id='sample', arm='normal', public_state='not_sealed')]
        echo, receipt = delivery_denominators(rows)
        self.assertEqual((echo['planned'], echo['unsealed'], echo['nonmatching_obtained']), (2, 1, 1))
        self.assertEqual(receipt['comparison_unknown_no_original'], 1)
        self.assertEqual(receipt['nonmatching_obtained'], 0)
        self.assertIsNone(receipt['match_rate_among_obtained'])

    def test_deny_arm_absence_remains_an_expected_permission_outcome(self):
        rows = [dict(card='S02', product_id='sample', arm='deny', public_state='sealed',
            verification=dict(echo_present=False, echo_bytes_equal=False,
                              receipt_present=False, receipt_declaration_valid=False), end={})]
        for row in delivery_denominators(rows):
            self.assertFalse(row['output_expected'])
            self.assertEqual(row['nonmatching_obtained'], 0)
            self.assertIsNone(row['match_rate_among_obtained'])


if __name__ == '__main__':
    unittest.main()
