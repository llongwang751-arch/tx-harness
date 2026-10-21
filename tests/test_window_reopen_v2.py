from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.window_reopen_v2 import close_verdict, direct_verdict, time_verdict


class WindowReopenV2Checks(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026, 10, 22, tzinfo=timezone.utc)

    def at(self, seconds):
        return (self.t+timedelta(seconds=seconds)).isoformat()

    def proof(self):
        return {'before_windows':[{'id':1}], 'close_started_at':self.at(0),
                'observations':[{'sequence':1,'at':self.at(1),'windows':[{'id':1}]},
                                {'sequence':2,'at':self.at(2),'windows':[]},
                                {'sequence':3,'at':self.at(3),'windows':[]}],
                'launch_at':self.at(4), 'restored_at':self.at(5), 'same_task':True}

    def test_verified_close_with_initial_nonempty_frame_passes(self):
        self.assertTrue(close_verdict(self.proof()))

    def test_launch_before_last_empty_observation_rejected(self):
        p=self.proof(); p['launch_at']=self.at(2.5)
        self.assertFalse(close_verdict(p))

    def test_single_empty_frame_and_wrong_task_rejected(self):
        p=self.proof(); p['observations']=p['observations'][1:]
        p['observations'][0]['sequence']=1; p['observations'][1]['sequence']=2
        p['observations'][0]['windows']=[{'id':1}]
        self.assertFalse(close_verdict(p))
        p=self.proof(); p['same_task']=False
        self.assertFalse(close_verdict(p))

    def test_late_close_evidence_rejected(self):
        p=self.proof(); p['observations'][-1]['at']=self.at(31)
        self.assertFalse(close_verdict(p))

    def test_direct_retrieval_requires_four_sources_and_original_bytes(self):
        with tempfile.TemporaryDirectory() as name:
            directory=Path(name); probe='核对\n  空格\n'.encode(); receipts=[]
            for phase in ('retrieval-before','retrieval-after'):
                (directory/phase).mkdir()
                for filename in ('probe.txt','stage-a.txt'):
                    relative=phase+'/'+filename; (directory/relative).write_bytes(probe)
                    receipts.append({'relative_path':relative,'method':'native_ui_save_as',
                      'source_scene':'source.ax','destination_scene':'dialog.ax',
                      'source_role':'original_message_attachment' if filename=='probe.txt' else 'native_stage_a_card',
                      'at':self.at(1),'bytes':len(probe),'sha256':hashlib.sha256(probe).hexdigest()})
            self.assertTrue(direct_verdict(probe,directory,receipts))
            self.assertFalse(direct_verdict(probe,directory,receipts[:-1]))
            receipts[-1]['method']='shell_copy'
            self.assertFalse(direct_verdict(probe,directory,receipts))
            receipts[-1]['method']='native_ui_save_as'
            (directory/receipts[-1]['relative_path']).write_bytes(b'changed')
            self.assertFalse(direct_verdict(probe,directory,receipts))

    def test_delay_cross_checked_against_wall_time(self):
        cp={'at':self.at(0)}
        self.assertTrue(time_verdict(cp,{'before_at':self.at(180),'delay_seconds':180}))
        self.assertFalse(time_verdict(cp,{'before_at':self.at(201),'delay_seconds':180}))


if __name__ == '__main__':
    unittest.main()
