"""Run only the new admission medication-coverage tests and fixed fixture."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from admission_medication_coverage_v1 import ROOT, VERSION, evaluate, load_fixture


def _write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable, "-B", str(ROOT / "test_admission_medication_coverage_v1.py")
    ]
    process = subprocess.run(
        command, capture_output=True, text=True, timeout=60, check=False
    )
    (output / "tests_stdout.txt").write_text(process.stdout, encoding="utf-8")
    (output / "tests_stderr.txt").write_text(process.stderr, encoding="utf-8")
    receipt = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "SYNTHETIC ONLY",
        "version": VERSION,
        "command": command,
        "exit_code": process.returncode,
        "raw_source_accessed": False,
        "source_gate": "NOT_ENTERED; no real MIMIC-IV source read attempted",
        "clinical_gates": {
            "CLINICAL_ACCEPTANCE": "HOLD",
            "AKI_ENDPOINT_READY": False,
            "ML_TRAINING_PERMITTED": False,
        },
    }
    if process.returncode:
        receipt["status"] = "FAIL"
        _write_exclusive(output / "execution_receipt.json", receipt)
        raise RuntimeError("New admission medication-coverage tests failed")

    packet = load_fixture()
    result = evaluate(packet)
    _write_exclusive(output / "invented_fixture.json", packet)
    _write_exclusive(output / "coverage_counts.json", result)
    code_files = (
        "admission_medication_coverage_v1.py",
        "admission_medication_coverage_v1.sql",
        "admission_medication_linkage_counts_v1.sql",
        "invented_admission_medication_fixture_v1.json",
        "test_admission_medication_coverage_v1.py",
        "run_admission_medication_coverage_v1.py",
    )
    receipt.update({
        "status": "PASS",
        "new_test_methods": 11,
        "result": result,
        "python": sys.version,
        "duckdb_version": __import__("duckdb").__version__,
        "code_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in code_files
        },
        "reused_sql_sha256": hashlib.sha256(
            (ROOT.parents[1] / "02_code" / "validation"
             / "aggregate_qc_medication_v1.sql").read_bytes()
        ).hexdigest(),
    })
    _write_exclusive(output / "execution_receipt.json", receipt)
    print(json.dumps({"status": "PASS", "new_tests": 11, "result": result}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
