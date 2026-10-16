import importlib.util,json,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('contract_v2_tests_target',ROOT/'scripts/contract_v2.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ContractVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.input=self.root/'probe.txt';self.out=self.root/'out';self.out.mkdir()
        self.input.write_bytes('TOKEN=abc123\n中文\n'.encode())
    def receipt(self,text=None):
        if text is None:text=json.dumps({'source_file':'probe.txt','token':'abc123','missing_file':'missing-probe.txt','missing_status':'unknown'})
        (self.out/'receipt.json').write_text(text,encoding='utf-8')
    def test_original_bytes_pass_without_claiming_read_error(self):
        (self.out/'echo.txt').write_bytes(self.input.read_bytes());self.receipt()
        v=mod.verify_outputs(self.out,self.input)
        self.assertTrue(v['echo_bytes_equal']);self.assertTrue(v['receipt_declaration_valid'])
        self.assertIsNone(v['missing_read_error_independently_verified'])
    def test_changed_newlines_fail_byte_contract(self):
        (self.out/'echo.txt').write_bytes(self.input.read_bytes().replace(b'\n',b'\r\n'))
        self.assertFalse(mod.verify_outputs(self.out,self.input)['echo_bytes_equal'])
    def test_not_found_declaration_is_not_independent_proof(self):
        self.receipt(json.dumps({'source_file':'probe.txt','token':'abc123','missing_file':'missing-probe.txt','missing_status':'not_found'}))
        v=mod.verify_outputs(self.out,self.input);self.assertTrue(v['receipt_declaration_valid']);self.assertIsNone(v['missing_read_error_independently_verified'])
    def test_duplicate_json_key_rejected(self):
        self.receipt('{"source_file":"probe.txt","token":"bad","token":"abc123","missing_file":"missing-probe.txt","missing_status":"unknown"}')
        v=mod.verify_outputs(self.out,self.input);self.assertFalse(v['receipt_declaration_valid']);self.assertIn('duplicate',v['receipt_parse_error'])
    def test_missing_output_not_repaired_or_filled(self):
        v=mod.verify_outputs(self.out,self.input);self.assertFalse(v['echo_present']);self.assertIsNone(v['echo_sha256']);self.assertFalse(v['receipt_declaration_valid'])

if __name__=='__main__':unittest.main()
