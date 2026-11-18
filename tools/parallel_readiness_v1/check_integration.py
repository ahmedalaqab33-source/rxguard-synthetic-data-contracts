"""Metadata/evidence-only checkpoint planner. Never opens candidate data files."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PureWindowsPath

GATES = {"CLINICAL_ACCEPTANCE": "HOLD", "AKI_ENDPOINT_READY": False,
         "ML_TRAINING_PERMITTED": False}
INVENTORY_COLUMNS = {"table", "filename", "path", "size_bytes", "inventory_status"}
# Minimum fields needed for the proposed integration tasks, not full release schemas.
REQUIRED = {
    "labevents": ("hosp", {"subject_id", "hadm_id", "itemid", "charttime", "valuenum", "valueuom"}),
    "d_labitems": ("hosp", {"itemid", "label", "fluid", "category"}),
    "d_items": ("icu", {"itemid", "label", "linksto", "unitname"}),
    "emar": ("hosp", {"subject_id", "hadm_id", "emar_id", "pharmacy_id", "charttime", "medication", "event_txt"}),
    "emar_detail": ("hosp", {"subject_id", "emar_id", "emar_seq", "dose_given", "dose_given_unit"}),
}


def evidence_payload(path):
    """Read an explicitly selected small evidence document, never a candidate."""
    if path.suffix.lower() not in {".csv", ".json"} or path.stat().st_size > 10_000_000:
        raise ValueError("Evidence must be CSV/JSON at most 10 MB")
    raw = path.read_bytes()
    return raw, {"filename": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def plan(rows, source_hash):
    for row in rows:
        if not INVENTORY_COLUMNS <= row.keys():
            raise ValueError("Inventory schema missing required columns")
    result = []
    for table, (module, columns) in REQUIRED.items():
        candidates = [r for r in rows if r["table"] == table]
        reasons = []
        if len(candidates) != 1:
            reasons.append("MISSING" if not candidates else "DUPLICATE_CANDIDATES")
        else:
            row = candidates[0]
            p = PureWindowsPath(row["path"])
            if not p.is_absolute() or str(p).startswith("\\\\"):
                reasons.append("NONLOCAL_OR_RELATIVE_PATH")
            if row["filename"] != table + ".csv.gz" or p.name != row["filename"]:
                reasons.append("PARTIAL_OR_NONCANONICAL_FILENAME")
            if p.parent.name.lower() != module:
                reasons.append("UNEXPECTED_MODULE_DIRECTORY")
            try:
                if int(row["size_bytes"]) <= 0:
                    reasons.append("ZERO_OR_NEGATIVE_BYTES")
            except (ValueError, TypeError):
                reasons.append("INVALID_SIZE")
            if row["inventory_status"] != "CANDIDATE_ONLY":
                reasons.append("INVENTORY_NOT_ELIGIBLE")
        result.append({"table": table, "expected_relative_path": f"{module}/{table}.csv.gz",
                       "candidate_count": len(candidates), "metadata_status": "BLOCKED" if reasons else "CANDIDATE_ONLY",
                       "blocking_reasons": reasons, "minimum_required_columns": sorted(columns),
                       "remaining_checkpoints": ["CONFIRM_DOWNLOAD_STOPPED_AND_STABLE", "VERIFY_ACCESS_AND_RELEASE_PROVENANCE",
                           "FULL_GZIP_SHA256_STABILITY_AUDIT", "COMPARE_AUTHENTICATED_DIGEST_IF_AVAILABLE",
                           "CHECK_ACTUAL_HEADER_AND_TYPES", "INDEPENDENT_CROSS_TABLE_REVIEW"],
                       "integration_permitted": False})
    return {"label": "PRELIMINARY — NOT CLINICALLY ADJUDICATED", "gates": dict(GATES),
            "inventory_sha256": source_hash, "mode": "EVIDENCE_ONLY_NO_CANDIDATE_DATA_READS",
            "source_provenance": "UNVERIFIED", "tables": result}


def schema_check(table, header):
    """Pure function for future authenticated header evidence or synthetic tests."""
    if table not in REQUIRED:
        raise ValueError("Unexpected table")
    if not isinstance(header, list) or any(not isinstance(x, str) for x in header):
        raise ValueError("Header must be a list of column names")
    if len(header) != len(set(header)):
        raise ValueError("Duplicate column names")
    missing = sorted(REQUIRED[table][1] - set(header))
    return {"schema_complete": not missing, "missing_columns": missing,
            "clinical_acceptance": "HOLD"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw, evidence = evidence_payload(args.inventory)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        parser.error("Missing or duplicate inventory header")
    if not INVENTORY_COLUMNS <= set(reader.fieldnames):
        parser.error("Inventory schema missing required columns")
    rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        parser.error("Malformed inventory row")
    report = plan(rows, evidence["sha256"])
    report["evidence"] = evidence
    # Exclusive creation prevents overwriting prior evidence or frozen artifacts.
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, indent=2, sort_keys=True, ensure_ascii=False)
        out.write("\n")
    print("CHECKPOINT_PLAN_WRITTEN; INTEGRATION_PERMITTED=FALSE; CLINICAL_ACCEPTANCE=HOLD")


if __name__ == "__main__":
    main()
