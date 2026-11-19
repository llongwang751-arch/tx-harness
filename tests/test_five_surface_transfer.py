import unittest

from scripts.audit_five_surface_transfer import parse_answer, parse_receipt


class TransferReceiptTests(unittest.TestCase):
    def test_reply_and_file_are_parsed_independently(self):
        receipt = '{"records":["A","B"],"total_cents":17}'
        expected = {'records': ['A', 'B'], 'total_cents': 17}
        self.assertEqual(parse_receipt(receipt), expected)
        self.assertEqual(parse_answer(f'已交付\n```json\n{receipt}\n```'), expected)
        self.assertIsNone(parse_receipt(f'```json\n{receipt}\n```'))

    def test_near_matches_violate_the_file_contract(self):
        for invalid in (
            '{"records":["A","B"],"total_cents":"17"}',
            '{"records":["A","B"],"total_cents":17.0}',
            '{"records":["A","B"],"total_cents":17,"total_cents":17}',
            '{"records":["A","B"],"total_cents":17,"note":"ok"}',
            '{"records":["A",2],"total_cents":17}',
        ):
            with self.subTest(response=invalid):
                self.assertIsNone(parse_receipt(invalid))
