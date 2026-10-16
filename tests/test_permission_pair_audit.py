import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_permission_pairs_v2 import normalize_launch,pair_summary

class PermissionPairAuditTest(unittest.TestCase):
    def rows(self):
        rows=[]
        for arm,access in [('allow','write'),('deny','read')]:
            rows.append({'slot_id':arm,'replicate':1,'arm':arm,'version':'v','requested_model':'m','input_sha256':'i','prompt_sha256':'p',
                'normalized_launch':{'positionals':['exe'],'config':{'permissions.harness_pilot.filesystem':{'<participant-workspace>':'write','<participant-workspace>/outputs':access},
                 'shell_environment_policy.set':{'canonical_value_sha256':'same'}}}})
        return rows
    def test_only_expected_override_passes(self):
        self.assertTrue(pair_summary(self.rows())[0]['all_recorded_checks_match'])
    def test_unexpected_environment_or_model_change_is_detected(self):
        for key in ('requested_model','environment'):
            rows=self.rows()
            if key=='environment':rows[1]['normalized_launch']['config']['shell_environment_policy.set']['canonical_value_sha256']='changed'
            else:rows[1][key]='changed'
            self.assertFalse(pair_summary(rows)[0]['all_recorded_checks_match'])
    def test_missing_permission_override_never_matches(self):
        rows=self.rows();rows[1]['normalized_launch']['config']['permissions.harness_pilot.filesystem'].pop('<participant-workspace>/outputs')
        self.assertFalse(pair_summary(rows)[0]['checks']['expected_output_overrides'])
    def test_unfinished_pair_not_inferred_from_one_arm(self):
        self.assertEqual(pair_summary(self.rows()[:1])[0]['state'],'incomplete')
    def test_private_paths_normalized_and_environment_values_omitted(self):
        args=['C:\\Users\\sample\\codex.exe','--cd','D:\\fixture','-c','permissions.harness_pilot.filesystem={"D:\\\\fixture\\\\outputs"="read"}',
              '-c','shell_environment_policy.set={"PRIVATE"="synthetic value"}']
        result=normalize_launch(args,'D:/fixture','D:/evaluator','C:/Users/sample')
        self.assertEqual(result['positionals'],['<user-home>/codex.exe','--cd','<participant-workspace>'])
        self.assertEqual(result['config']['permissions.harness_pilot.filesystem'],{'<participant-workspace>/outputs':'read'})
        self.assertNotIn('synthetic value',str(result));self.assertNotIn('sample',str(result))

if __name__=='__main__':unittest.main()
