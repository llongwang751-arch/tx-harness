import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from filter_contract_native import project,safe_target,field_hash

class ContractPrivacyTest(unittest.TestCase):
    def pair(self,tool,params,result):
        return [{'received_at':'t1','event':{'type':'tool_call','callId':'c','tool':tool,'input':params}},
                {'received_at':'t2','event':{'type':'tool_result','callId':'c','status':'completed','result':result}}]
    def test_skill_body_never_reaches_evaluator_projection(self):
        rows=self.pair('skill',{'name':'synthetic','body':'DO NOT DISPLAY'},'SYNTHETIC SKILL BODY')
        result,audit=project(rows,'D:/fixture')
        self.assertNotIn('input',result[0]['event']);self.assertNotIn('result',result[1]['event'])
        self.assertEqual(result[1]['event']['status'],'completed')
        self.assertEqual(audit[1]['original_field_sha256'],field_hash('SYNTHETIC SKILL BODY'))
        self.assertEqual(rows[1]['event']['result'],'SYNTHETIC SKILL BODY')
    def test_skill_file_read_is_elided_even_with_read_tool(self):
        result,audit=project(self.pair('read',{'file_path':'D:/private/SKILL.md'},'private body'),'D:/fixture')
        self.assertNotIn('result',result[1]['event']);self.assertEqual(len(audit),2)
    def test_synthetic_read_error_and_write_literal_are_unchanged(self):
        for tool,params,value in [('read',{'file_path':'inputs/missing-probe.txt'},'not found'),
                                  ('write',{'file_path':'outputs/echo.txt','content':'固定\n'},'Created file')]:
            rows=self.pair(tool,params,value);result,audit=project(rows,'D:/fixture')
            self.assertEqual(result,rows);self.assertEqual(audit,[])
    def test_unpaired_unknown_result_fails_closed(self):
        rows=[{'event':{'type':'tool_result','callId':'unknown','status':'error','result':'unclassified body'}}]
        result,audit=project(rows,'D:/fixture');self.assertNotIn('result',result[0]['event'])
        self.assertEqual(result[0]['event']['status'],'error');self.assertEqual(audit[0]['source_physical_line'],1)
    def test_target_normalization_does_not_allow_prefix_escape(self):
        self.assertTrue(safe_target('D:\\fixture\\inputs\\probe.txt','D:/fixture'))
        self.assertFalse(safe_target('D:/fixture-other/inputs/probe.txt','D:/fixture'))
        self.assertFalse(safe_target('inputs/../../private/SKILL.md','D:/fixture'))
    def test_command_referencing_skill_body_is_elided(self):
        rows=self.pair('pwsh',{'command':'Get-Content SKILL.md'},'private body')
        result,audit=project(rows,'D:/fixture');self.assertEqual(len(audit),2)
        self.assertNotIn('result',result[1]['event'])

if __name__=='__main__':unittest.main()
