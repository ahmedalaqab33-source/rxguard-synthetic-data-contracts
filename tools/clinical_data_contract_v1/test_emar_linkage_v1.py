import unittest
from copy import deepcopy
from emar_linkage_v1 import summarize,invented_fixture

class LinkageTests(unittest.TestCase):
    def test_exact_counts_and_no_fanout(self):
        self.assertEqual(summarize(invented_fixture()),{'parent_rows':7,'parent_missing_key_rows':1,'parent_duplicate_keys':1,'unique_parent_keys':4,'detail_rows':8,'classified_detail_rows':8,'missing_key_detail_rows':1,'orphan_detail_rows':2,'ambiguous_parent_detail_rows':1,'unique_parent_link_detail_rows':4,'unique_parents_without_detail':1,'max_details_per_unique_parent':2})
    def test_composite_subject_and_sequence_isolation(self):
        p=invented_fixture();p['parents']=p['parents'][:1];p['details']=[p['details'][5],p['details'][6]]
        self.assertEqual(summarize(p)['orphan_detail_rows'],2)
    def test_multiple_children_not_deduplicated(self):
        p=invented_fixture();p['parents']=p['parents'][:1];p['details']=p['details'][:2];r=summarize(p)
        self.assertEqual(r['unique_parent_link_detail_rows'],2);self.assertEqual(r['max_details_per_unique_parent'],2)
    def test_null_keys_never_join(self):
        p=invented_fixture();p['parents']=[p['parents'][4]];p['details']=[p['details'][4]];r=summarize(p)
        self.assertEqual(r['missing_key_detail_rows'],1);self.assertEqual(r['unique_parent_link_detail_rows'],0)
    def test_empty_inputs(self):
        self.assertTrue(all(v==0 for v in summarize(dict(scope='SYNTHETIC',invented=True,parents=[],details=[])).values()))
    def test_missing_parents_and_missing_details(self):
        p=invented_fixture();p['parents']=[];r=summarize(p);self.assertEqual(r['orphan_detail_rows'],7)
        p=invented_fixture();p['details']=[];self.assertEqual(summarize(p)['unique_parents_without_detail'],4)
    def test_unmarked_malformed_and_duplicate_row_ids_rejected(self):
        for mutation in [lambda p:p.update(invented=False),lambda p:p['details'][0].update(scope='REAL'),lambda p:p['details'][0].update(subject_id=True),lambda p:p['details'][0].update(emar_id=''),lambda p:p['details'][0].update(extra=1),lambda p:p['details'].append(deepcopy(p['details'][0]))]:
            p=invented_fixture();mutation(p)
            with self.assertRaises(ValueError):summarize(p)
    def test_nonmutation_and_permutation(self):
        p=invented_fixture();before=deepcopy(p);r=summarize(p);self.assertEqual(before,p);p['parents'].reverse();p['details'].reverse();self.assertEqual(r,summarize(p))

if __name__=='__main__':unittest.main(verbosity=2)
