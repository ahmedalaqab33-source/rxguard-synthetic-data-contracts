import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from check_integration import GATES, REQUIRED, plan, schema_check


def row(table="labevents"):
    module = REQUIRED[table][0]
    return dict(table=table, filename=table+".csv.gz", path=f"D:\\data\\{module}\\{table}.csv.gz",
                size_bytes="500", inventory_status="CANDIDATE_ONLY")


class IntegrationTests(unittest.TestCase):
    def test_missing_all(self):
        self.assertTrue(all(x["blocking_reasons"] == ["MISSING"] for x in plan([], "x")["tables"]))

    def test_complete_metadata_never_integrates(self):
        p = plan([row(t) for t in REQUIRED], "abc")
        self.assertEqual(p["gates"], GATES)
        self.assertTrue(all(x["metadata_status"] == "CANDIDATE_ONLY" and not x["integration_permitted"] for x in p["tables"]))
        self.assertEqual(p["source_provenance"], "UNVERIFIED")

    def test_bad_candidates(self):
        cases = [({"filename": "labevents.csv.gz.part"}, "PARTIAL_OR_NONCANONICAL_FILENAME"),
                 ({"size_bytes": "0"}, "ZERO_OR_NEGATIVE_BYTES"),
                 ({"size_bytes": "-1"}, "ZERO_OR_NEGATIVE_BYTES"),
                 ({"size_bytes": "x"}, "INVALID_SIZE"),
                 ({"inventory_status": "INCOMPLETE_DOWNLOAD"}, "INVENTORY_NOT_ELIGIBLE"),
                 ({"path": "relative.csv.gz"}, "NONLOCAL_OR_RELATIVE_PATH"),
                 ({"path": r"\\server\hosp\labevents.csv.gz"}, "NONLOCAL_OR_RELATIVE_PATH"),
                 ({"path": r"D:\data\icu\labevents.csv.gz"}, "UNEXPECTED_MODULE_DIRECTORY")]
        for changes, reason in cases:
            with self.subTest(changes=changes):
                r = row(); r.update(changes)
                self.assertIn(reason, plan([r], "x")["tables"][0]["blocking_reasons"])

    def test_duplicate_candidates(self):
        self.assertEqual(plan([row(), row()], "x")["tables"][0]["blocking_reasons"], ["DUPLICATE_CANDIDATES"])

    def test_schema_rejected(self):
        with self.assertRaises(ValueError):
            plan([{"table": "labevents"}], "x")

    def test_actual_schema_contract(self):
        for table, (_, columns) in REQUIRED.items():
            self.assertTrue(schema_check(table, sorted(columns))["schema_complete"])
            self.assertFalse(schema_check(table, [])["schema_complete"])
        with self.assertRaises(ValueError):
            schema_check("labevents", ["subject_id", "subject_id"])
        with self.assertRaises(ValueError):
            schema_check("unknown", [])

    def test_no_file_reads_in_plan(self):
        with patch.object(Path, "open", side_effect=AssertionError("Data opened")):
            plan([row()], "x")

    def test_deterministic_and_does_not_mutate(self):
        rows = [row(t) for t in REQUIRED]; before = copy.deepcopy(rows)
        self.assertEqual(plan(rows, "x"), plan(list(reversed(rows)), "x"))
        self.assertEqual(rows, before)

    def test_cli_evidence_hash_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            inventory = Path(temp)/"inventory.csv"; output = Path(temp)/"out.json"
            inventory.write_text("table,filename,path,size_bytes,inventory_status\n", encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).with_name("check_integration.py")), "--inventory", str(inventory), "--output", str(output)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["inventory_sha256"], hashlib.sha256(inventory.read_bytes()).hexdigest())
            before = output.read_bytes()
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(before, output.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
