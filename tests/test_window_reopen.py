import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.window_reopen import judge


class WindowReopenChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.probe = '核对\n  空格\n'.encode('utf-8')
        for name in ('stage-a.txt', 'stage-b.txt'):
            (self.out / name).write_bytes(self.probe)
        self.receipt = {'stage': 'B', 'source': 'probe.txt', 'bytes': len(self.probe),
                        'sha256': hashlib.sha256(self.probe).hexdigest()}
        self.write_receipt(self.receipt)

    def write_receipt(self, obj):
        (self.out / 'receipt.json').write_text(json.dumps(obj, indent=3), encoding='utf-8')

    def test_positive_and_formatting(self):
        self.assertTrue(judge(self.probe, self.out)['joint_delivery_pass'])

    def test_newline_conversion_rejected(self):
        (self.out / 'stage-b.txt').write_bytes(self.probe.replace(b'\n', b'\r\n'))
        self.assertFalse(judge(self.probe, self.out)['joint_delivery_pass'])

    def test_missing_file_is_not_success(self):
        (self.out / 'stage-a.txt').unlink()
        self.assertFalse(judge(self.probe, self.out)['joint_delivery_pass'])

    def test_extra_key_wrong_type_and_wrong_digest_rejected(self):
        for key, value in [('extra', 1), ('bytes', float(len(self.probe))), ('sha256', '0'*64)]:
            with self.subTest(key=key):
                self.write_receipt({**self.receipt, key: value})
                self.assertFalse(judge(self.probe, self.out)['joint_delivery_pass'])

    def test_duplicate_key_rejected(self):
        content = json.dumps(self.receipt)[:-1] + ', "stage":"B"}'
        (self.out / 'receipt.json').write_text(content, encoding='utf-8')
        self.assertFalse(judge(self.probe, self.out)['joint_delivery_pass'])


if __name__ == '__main__':
    unittest.main()
