import unittest
from copy import deepcopy
from contract import load_fixture,evaluate,aggregate,validate

class ContractTests(unittest.TestCase):
    def setUp(self):self.p=load_fixture()
    def test_join_does_not_fan_out_duplicate_dictionary(self):
        rows=evaluate(self.p);self.assertEqual(len(rows),12);self.assertEqual(rows[1]['linkage_state'],'AMBIGUOUS_DICTIONARY_KEY');self.assertEqual(rows[1]['unit_state'],'NOT_ASSESSED')
    def test_missing_unmatched_wrong_module(self):
        rows=evaluate(self.p)
        self.assertEqual([rows[i]['linkage_state'] for i in [2,3,4]],['UNMATCHED_KEY','MISSING_KEY','LINKSTO_MISMATCH'])
    def test_unknown_and_literal_units(self):
        rows=evaluate(self.p);self.assertEqual([rows[i]['unit_state'] for i in [0,5,6,11]],['LITERAL_MATCH','UNKNOWN','LITERAL_MISMATCH','UNKNOWN'])
    def test_temporal_boundary_and_unknown(self):
        rows=evaluate(self.p);self.assertEqual([rows[i]['availability_state'] for i in [7,9,10]],['AFTER','UNKNOWN','AT_OR_BEFORE']);self.assertEqual(rows[8]['interval_state'],'REVERSED')
    def test_no_implicit_delivery_or_drug_classification(self):
        rows=evaluate(self.p);self.assertEqual(rows[0]['status_state'],'PRESENT_UNINTERPRETED');self.assertEqual(rows[11]['status_state'],'MISSING_UNINTERPRETED');self.assertEqual(set(rows[0]),{'row_id','linkage_state','unit_state','interval_state','availability_state','status_state'})
    def test_malformed_unmarked_and_type_inputs_rejected(self):
        for mutate in [lambda p:p.update(invented=False),lambda p:p.update(scope='REAL'),lambda p:p['events'][0].update(scope='REAL'),lambda p:p['events'][0].update(itemid=True),lambda p:p['events'][0].update(storetime='garbage'),lambda p:p['events'][0].update(patient_id='x'),lambda p:p['events'][0].update(row_id=None)]:
            p=deepcopy(self.p);mutate(p)
            with self.subTest(p=p):
                with self.assertRaises(ValueError):evaluate(p)
    def test_duplicate_events_rejected_not_silently_deduplicated(self):
        self.p['events'].append(deepcopy(self.p['events'][0]))
        with self.assertRaises(ValueError):evaluate(self.p)
    def test_empty_inputs_preserve_zero_counts(self):
        self.p['dictionary']=[];self.p['events']=[];self.assertEqual(evaluate(self.p),[]);self.assertTrue(all(x==0 for x in aggregate(self.p,[]).values()))
    def test_permutation_determinism_and_nonmutation(self):
        before=deepcopy(self.p);expected=evaluate(self.p);self.assertEqual(before,self.p);self.p['dictionary'].reverse();self.p['events'].reverse();self.assertEqual(expected,evaluate(self.p))
    def test_unknown_linksto_and_missing_interval(self):
        self.p['dictionary'][0]['linksto']=None;self.p['events'][0]['starttime']=None
        row=evaluate(self.p)[0];self.assertEqual(row['linkage_state'],'UNKNOWN_LINKSTO');self.assertEqual(row['interval_state'],'UNKNOWN')
    def test_exact_manual_aggregate_counts(self):
        result=aggregate(self.p,evaluate(self.p));self.assertEqual(result['dictionary_duplicate_keys'],1);self.assertEqual(result['dictionary_null_key_rows'],1);self.assertEqual(result['linkage_state.UNIQUE_INPUTEVENTS_LINK'],8);self.assertEqual(result['availability_state.AT_OR_BEFORE'],10)

if __name__=='__main__':unittest.main(verbosity=2)
