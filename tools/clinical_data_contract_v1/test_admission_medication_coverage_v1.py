import unittest
from copy import deepcopy

from admission_medication_coverage_v1 import evaluate, load_fixture


class AdmissionMedicationCoverageTests(unittest.TestCase):
    def test_exact_admission_counts_and_source_separation(self):
        result = evaluate(load_fixture())
        rows = {row["hadm_id"]: row for row in result["admission_coverage"]}
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            (
                rows[8101]["prescription_order_evidence_rows"],
                rows[8101]["pharmacy_order_evidence_rows"],
                rows[8101]["emar_record_rows"],
                rows[8101]["linked_administration_detail_evidence_rows"],
            ),
            (1, 2, 4, 3),
        )
        self.assertEqual(
            (
                rows[8102]["prescription_order_evidence_rows"],
                rows[8102]["pharmacy_order_evidence_rows"],
                rows[8102]["emar_record_rows"],
                rows[8102]["linked_administration_detail_evidence_rows"],
            ),
            (1, 1, 1, 1),
        )
        self.assertEqual(
            (
                rows[8201]["prescription_order_evidence_rows"],
                rows[8201]["pharmacy_order_evidence_rows"],
                rows[8201]["emar_record_rows"],
                rows[8201]["linked_administration_detail_evidence_rows"],
            ),
            (0, 0, 0, 0),
        )

    def test_order_pharmacy_identity_uses_existing_three_key_logic(self):
        result = evaluate(load_fixture())
        self.assertEqual(
            result["order_pharmacy_linkage_counts_as_of_admission_index"],
            {
                "missing_identity_key": 0,
                "ambiguous_duplicate_key": 1,
                "pharmacy_id_present_identity_discordant": 0,
                "unmatched": 0,
                "unique_three_key_candidate": 1,
            },
        )

    def test_detail_linkage_partitions_missing_ambiguous_and_unmatched(self):
        result = evaluate(load_fixture())
        self.assertEqual(result["detail_linkage_rows_as_of_snapshot"], 7)
        self.assertEqual(
            result["detail_linkage_counts_as_of_snapshot"],
            {
                "AMBIGUOUS_PARENT": 1,
                "MISSING_KEY": 1,
                "UNMATCHED_PARENT": 1,
                "UNIQUE_PARENT_LINK": 4,
            },
        )

    def test_unknown_status_is_never_interpreted_as_administration(self):
        packet = load_fixture()
        rows = {row["hadm_id"]: row for row in evaluate(packet)["admission_coverage"]}
        self.assertEqual(rows[8101]["administration_status_unknown_emar_rows"], 4)
        self.assertEqual(rows[8101]["emar_status_missing_rows"], 1)
        self.assertEqual(rows[8101]["emar_status_present_uninterpreted_rows"], 3)
        self.assertEqual(rows[8102]["administration_status_unknown_emar_rows"], 1)
        packet["emar"][1]["status_text"] = ""
        blank_status = {
            row["hadm_id"]: row
            for row in evaluate(packet)["admission_coverage"]
        }
        self.assertEqual(blank_status[8101]["emar_status_missing_rows"], 2)
        self.assertEqual(blank_status[8101]["administration_status_unknown_emar_rows"], 4)

    def test_future_event_and_future_availability_are_excluded(self):
        packet = load_fixture()
        baseline = evaluate(packet)
        packet["orders"].append({
            "scope": "SYNTHETIC", "row_id": "INVENTED-FUTURE-ORDER",
            "source": "PRESCRIPTION", "subject_id": 7001, "hadm_id": 8101,
            "pharmacy_id": "RX-FUTURE", "event_time": "2100-01-01 11:00:00",
            "available_time": "2100-01-01 12:00:01",
        })
        packet["emar"].append({
            "scope": "SYNTHETIC", "row_id": "INVENTED-FUTURE-EMAR",
            "subject_id": 7001, "hadm_id": 8101, "emar_id": "E-FUTURE",
            "emar_seq": 1, "event_time": "2100-01-01 11:00:00",
            "available_time": "2100-01-01 12:00:01",
            "status_text": "INVENTED_FUTURE_STATUS",
        })
        packet["details"].append({
            "scope": "SYNTHETIC", "row_id": "INVENTED-FUTURE-DETAIL",
            "subject_id": 7001, "emar_id": "E-A", "emar_seq": 1,
            "event_time": "2100-01-01 11:00:00",
            "available_time": "2100-01-01 12:00:01",
        })
        self.assertEqual(evaluate(packet), baseline)

    def test_duplicate_emar_parent_does_not_fan_out_detail_counts(self):
        packet = load_fixture()
        rows = {row["hadm_id"]: row for row in evaluate(packet)["admission_coverage"]}
        self.assertEqual(rows[8101]["linked_administration_detail_evidence_rows"], 3)
        self.assertEqual(
            evaluate(packet)["detail_linkage_counts_as_of_snapshot"]["AMBIGUOUS_PARENT"],
            1,
        )

    def test_order_evidence_is_not_multiplied_by_emar_or_detail_rows(self):
        packet = load_fixture()
        before = evaluate(packet)
        packet["details"].append({
            "scope": "SYNTHETIC", "row_id": "INVENTED-EXTRA-CHILD",
            "subject_id": 7001, "emar_id": "E-A", "emar_seq": 1,
            "event_time": "2100-01-01 11:30:00",
            "available_time": "2100-01-01 11:40:00",
        })
        after = evaluate(packet)
        before_rows = {row["hadm_id"]: row for row in before["admission_coverage"]}
        after_rows = {row["hadm_id"]: row for row in after["admission_coverage"]}
        self.assertEqual(
            [
                (before_rows[key]["prescription_order_evidence_rows"],
                 before_rows[key]["pharmacy_order_evidence_rows"])
                for key in before_rows
            ],
            [
                (after_rows[key]["prescription_order_evidence_rows"],
                 after_rows[key]["pharmacy_order_evidence_rows"])
                for key in after_rows
            ],
        )

    def test_temporal_unknown_is_not_counted_as_observed(self):
        packet = load_fixture()
        baseline = evaluate(packet)
        packet["orders"][0]["available_time"] = None
        changed = evaluate(packet)
        base_rows = {row["hadm_id"]: row for row in baseline["admission_coverage"]}
        changed_rows = {row["hadm_id"]: row for row in changed["admission_coverage"]}
        self.assertEqual(base_rows[8101]["prescription_order_evidence_rows"], 1)
        self.assertEqual(changed_rows[8101]["prescription_order_evidence_rows"], 0)

    def test_malformed_or_noninvented_inputs_are_rejected(self):
        mutations = [
            lambda p: p.update(invented=False),
            lambda p: p["orders"][0].update(scope="REAL"),
            lambda p: p["emar"][0].update(emar_seq=True),
            lambda p: p["details"][0].update(event_time="not-a-time"),
            lambda p: p["admissions"][0].update(hadm_id=True),
            lambda p: p["orders"][0].update(extra_field="not allowed"),
            lambda p: p["emar"].append(deepcopy(p["emar"][0])),
        ]
        for mutate in mutations:
            packet = load_fixture()
            mutate(packet)
            with self.subTest(packet=packet):
                with self.assertRaises(ValueError):
                    evaluate(packet)

    def test_deterministic_nonmutating_and_gate_preserving(self):
        packet = load_fixture()
        original = deepcopy(packet)
        first = evaluate(packet)
        self.assertEqual(packet, original)
        packet["details"].reverse()
        packet["emar"].reverse()
        packet["orders"].reverse()
        self.assertEqual(first, evaluate(packet))
        self.assertEqual(first["clinical_gates"]["CLINICAL_ACCEPTANCE"], "HOLD")
        self.assertFalse(first["clinical_gates"]["AKI_ENDPOINT_READY"])
        self.assertFalse(first["clinical_gates"]["ML_TRAINING_PERMITTED"])
        self.assertNotIn("exposure", str(first).lower())
        self.assertNotIn("aki", str(first["admission_coverage"]).lower())

    def test_empty_evidence_keeps_one_zero_coverage_row_per_admission(self):
        packet = load_fixture()
        packet["orders"] = []
        packet["emar"] = []
        packet["details"] = []
        result = evaluate(packet)
        self.assertEqual(len(result["admission_coverage"]), 3)
        self.assertEqual(result["detail_linkage_rows_as_of_snapshot"], 0)
        self.assertTrue(all(
            row["prescription_order_evidence_rows"] == 0
            and row["pharmacy_order_evidence_rows"] == 0
            and row["emar_record_rows"] == 0
            and row["linked_administration_detail_evidence_rows"] == 0
            for row in result["admission_coverage"]
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
