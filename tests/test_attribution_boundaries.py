"""Prevent overclaiming controls or selecting only successful boundary traces."""
from copy import deepcopy
import unittest

from scripts import audit_attribution_boundaries as audit


class AttributionBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=audit.read(audit.ROOT/audit.ASSESSMENT)
        cls.coverage=audit.read(audit.ROOT/audit.COVERAGE)

    def test_all_five_reviewed_sources_and_generated_denominators(self):
        data=audit.build(self.spec)
        self.assertEqual(data['source_s01_runs_reviewed'],15)
        self.assertEqual(data['new_independent_product_runs'],0)
        self.assertFalse(data['pure_harness_ranking_supported'])
        self.assertTrue(all(r['pure_harness_causal_score'] is None for r in data['products']))

    def test_same_label_cannot_be_promoted_to_backend_attestation(self):
        spec=deepcopy(self.spec)
        spec['products'][1]['model_control']='same_backend_verified'
        with self.assertRaisesRegex(ValueError,'backend attestation'):
            audit.validate_assessment(spec)

    def test_partial_skill_shutdown_is_not_complete(self):
        spec=deepcopy(self.spec)
        spec['products'][2]['all_skills_disabled_attested']=True
        with self.assertRaisesRegex(ValueError,'Skill control'):
            audit.validate_assessment(spec)

    def test_unknown_skill_state_is_not_disabled(self):
        spec=deepcopy(self.spec)
        spec['products'][3]['skill_control']='disabled'
        with self.assertRaisesRegex(ValueError,'Skill control'):
            audit.validate_assessment(spec)

    def test_artifact_or_pair_pass_does_not_allow_pure_harness_claim(self):
        spec=deepcopy(self.spec)
        spec['products'][0]['independent_harness_causal_claim']=True
        with self.assertRaisesRegex(ValueError,'Independent Harness'):
            audit.validate_assessment(spec)

    def test_old_source_review_cannot_inflate_run_count_or_rank(self):
        for field,value in [('new_product_runs',15),('pure_harness_ranking_supported',True)]:
            spec=deepcopy(self.spec);spec[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit.validate_assessment(spec)

    def test_missing_product_or_round_cannot_be_hidden(self):
        spec=deepcopy(self.spec);spec['products'].pop()
        with self.assertRaisesRegex(ValueError,'five distinct'):
            audit.validate_assessment(spec)
        spec=deepcopy(self.spec);spec['products'][0]['evidence'].pop(0)
        with self.assertRaisesRegex(ValueError,'three configurations'):
            audit.validate_assessment(spec)

    def test_missing_source_locator_or_private_path_is_rejected(self):
        spec=deepcopy(self.spec)
        spec['products'][0]['evidence'][0]['json_pointer']='/visible_conditions/not_a_recorded_field'
        with self.assertRaises((ValueError,KeyError)):
            audit.verify_sources(spec)
        for path in ['private/record.json','../private/record.json','C:/private/record.json',
                     r'public\..\private\record.json']:
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'public repository'):
                audit.public_path(path)

    def test_source_hash_change_is_not_a_new_control(self):
        spec=deepcopy(self.spec);spec['products'][0]['evidence'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'reference hash'):
            audit.verify_sources(spec)

    def test_upstream_deviation_must_remain_in_all_attempts(self):
        c=deepcopy(self.coverage)
        c['rows']=[r for r in c['rows'] if r['slot_id']!='S01-dsh-r1']
        with self.assertRaisesRegex(ValueError,'only successful'):
            audit.product_metrics(c,'dsh')

    def test_unknown_eligibility_is_not_a_known_product_failure(self):
        metrics,_=audit.product_metrics(self.coverage,'yuanbao')
        for row in metrics:
            self.assertEqual((row['public_started'],row['eligible'],row['failed'],
                              row['unknown_verdict'],row['eligibility_not_attested']),(3,0,0,3,3))

    def test_eligible_denominator_cannot_hide_missing_or_upstream_round(self):
        c=deepcopy(self.coverage)
        row=next(r for r in c['metric_denominators'] if r['product_id']=='dsh' and
                 r['card']=='S01' and r['metric']=='missing_feedback')
        row['public_started']=2
        with self.assertRaisesRegex(ValueError,'all three attempts'):
            audit.product_metrics(c,'dsh')
        metrics,_=audit.product_metrics(self.coverage,'dsh')
        row=next(r for r in metrics if r['metric']=='missing_feedback')
        self.assertEqual((row['public_started'],row['eligible'],row['passed'],row['upstream_deviation']),(3,2,2,1))

    def test_stop_gate_cannot_be_relabelled_as_executed_experiment(self):
        spec=deepcopy(self.spec);spec['new_experiment_decision']['execute_now']=True
        with self.assertRaisesRegex(ValueError,'stop/reopen'):
            audit.validate_assessment(spec)


if __name__=='__main__':
    unittest.main()
