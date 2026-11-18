import unittest
from trace import assess_trace
from copy import deepcopy

class TraceTests(unittest.TestCase):
    def fixture(self):
        return dict(scope='SYNTHETIC', evidence_id='invented-1', source_locator='synthetic://fixture', source_digest='a'*64, policy_version='proposal-1', event_time='2020-01-01T10:00:00+00:00', available_time='2020-01-01T10:30:00+00:00', decision_time='2020-01-01T11:00:00+00:00', release_status='SYNTHETIC_ACCEPTED')
    def test_eligible_trace_does_not_promote_gates(self):
        result=assess_trace(self.fixture(),synthetic=True)
        self.assertTrue(result['trace_eligible']); self.assertEqual(result['gates'],dict(CLINICAL_ACCEPTANCE='HOLD',AKI_ENDPOINT_READY=False,ML_TRAINING_PERMITTED=False))
    def test_late_documentation_is_leakage(self):
        t=self.fixture();t['available_time']='2020-01-01T12:00:00+00:00'
        self.assertEqual(assess_trace(t,synthetic=True)['reasons'],['NOT_YET_AVAILABLE'])
    def test_equivalent_zone_boundary(self):
        t=self.fixture();t['available_time']='2020-01-01T14:00:00+03:00'
        self.assertTrue(assess_trace(t,synthetic=True)['trace_eligible'])
    def test_unknown_source_is_not_accepted(self):
        t=self.fixture();t['release_status']='PENDING'
        self.assertEqual(assess_trace(t,synthetic=True)['reasons'],['UNACCEPTED_SOURCE_ASSERTION'])
    def test_future_event(self):
        t=self.fixture();t['event_time']='2020-01-02T10:00:00+00:00'
        self.assertIn('FUTURE_EVENT',assess_trace(t,synthetic=True)['reasons'])
    def test_scope_incomplete_digest_timezone_rejected(self):
        for field,value in [('scope','RESTRICTED'),('source_digest','invalid'),('policy_version',''),('event_time','2020-01-01T10:00:00')]:
            t=self.fixture();t[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): assess_trace(t,synthetic=True)
        with self.assertRaises(ValueError): assess_trace(self.fixture())
if __name__=='__main__': unittest.main()
