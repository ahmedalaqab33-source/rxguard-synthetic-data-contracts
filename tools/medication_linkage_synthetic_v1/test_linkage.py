import unittest
from linkage import audit, interval


def row(subject='1', hadm='10', pid='100', start='2020-01-01 01:00:00', stop='2020-01-01 03:00:00'):
    return dict(subject_id=subject, hadm_id=hadm, pharmacy_id=pid, starttime=start, stoptime=stop)


class LinkageTests(unittest.TestCase):
    def test_three_keys_no_identity_repair(self):
        r = audit([row(), row(pid='200')], [row(subject='2'), row(hadm='11', pid='200')], synthetic=True)
        self.assertEqual(r['linkage'], {'pharmacy_id_present_identity_discordant': 2})
        self.assertEqual(r['unique_candidate_temporal'], {})

    def test_duplicates_never_inflate_or_resolve(self):
        r = audit([row(), row()], [row(), row()], synthetic=True)
        self.assertEqual(r['linkage'], {'ambiguous_duplicate_key': 2})
        self.assertEqual(r['duplicate_pharmacy_key_groups'], 1)
        self.assertEqual(r['duplicate_prescription_key_groups'], 1)
        self.assertEqual(r['unique_candidate_temporal'], {})

    def test_nulls_never_match_nulls(self):
        r = audit([row(pid=None), row(subject=' ')], [row(pid=None)], synthetic=True)
        self.assertEqual(r['linkage'], {'missing_identity_key': 2})

    def test_overlap_touching_disjoint(self):
        base = row()
        self.assertEqual(audit([base], [base], synthetic=True)['unique_candidate_temporal'], {'overlap': 1})
        for start in ('2020-01-01 03:00:00', '2020-01-02 01:00:00'):
            other = row(start=start, stop='2020-01-03 00:00:00')
            self.assertEqual(audit([base], [other], synthetic=True)['unique_candidate_temporal'], {'nonoverlap': 1})

    def test_timestamp_partition_and_missing_overlap(self):
        fixtures = [row(start=None, stop=''), row(start=None), row(stop=None), row(start='bad'),
                    row(start='2020-01-02'), row(stop='2020-01-01 01:00:00'), row()]
        expected = ['both_missing', 'start_missing', 'stop_missing', 'invalid_timestamp', 'negative', 'zero', 'positive']
        self.assertEqual([interval(r)[0] for r in fixtures], expected)
        r = audit(fixtures, [row()], synthetic=True)
        self.assertEqual(sum(r['timestamp_partitions']['prescriptions'].values()), 7)
        self.assertEqual(r['unique_candidate_temporal'], {'not_evaluable': 6, 'overlap': 1})

    def test_missing_unmatched_empty_and_gates(self):
        r = audit([row()], [], synthetic=True)
        self.assertEqual(r['linkage'], {'unmatched': 1})
        self.assertEqual(r['CLINICAL_ACCEPTANCE'], 'HOLD')
        self.assertFalse(r['AKI_ENDPOINT_READY'])
        self.assertFalse(r['ML_TRAINING_PERMITTED'])
        self.assertEqual(audit([], [], synthetic=True)['linkage'], {})

    def test_schema_scope_rejection(self):
        with self.assertRaises(ValueError): audit([], [])
        with self.assertRaises(ValueError): audit([{}], [], synthetic=True)
        with self.assertRaises(TypeError): audit([row(pid=100)], [], synthetic=True)

    def test_order_determinism_no_mutation(self):
        p = [row(), row(pid='200'), row(subject=None)]
        q = [row(), row(pid='200')]
        before = [dict(r) for r in p]
        self.assertEqual(audit(p, q, synthetic=True), audit(p[::-1], q[::-1], synthetic=True))
        self.assertEqual(p, before)

    def test_timezone_requires_review(self):
        self.assertEqual(interval(row(start='2020-01-01T01:00:00+00:00'))[0], 'invalid_timestamp')


if __name__ == '__main__':
    unittest.main()
