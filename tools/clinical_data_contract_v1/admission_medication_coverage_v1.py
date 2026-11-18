"""Synthetic-only admission medication-evidence coverage aggregation."""
from datetime import datetime
import json
from pathlib import Path

import duckdb

from contract import timestamp
from emar_linkage_v1 import validate as validate_emar_linkage

VERSION = "synthetic-admission-medication-coverage-0.1.0"
ROOT = Path(__file__).resolve().parent
ORDER_LINKAGE_SQL_PATH = (
    ROOT.parents[1] / "02_code" / "validation" / "aggregate_qc_medication_v1.sql"
)
ORDER_LINKAGE_STATES = (
    "missing_identity_key",
    "ambiguous_duplicate_key",
    "pharmacy_id_present_identity_discordant",
    "unmatched",
    "unique_three_key_candidate",
)


def _validate_optional_timestamp(value):
    if value is not None:
        timestamp(value)


def _validate_identifier(value, *, nullable):
    if value is None and nullable:
        return
    if type(value) is not int or value <= 0 or value >= 2**63:
        raise ValueError("Expected a positive bounded integer identifier or null")


def _validate_text(value, *, nullable, limit=200, allow_blank=False):
    if value is None and nullable:
        return
    if (
        not isinstance(value, str)
        or (not allow_blank and not value.strip())
        or len(value) > limit
    ):
        raise ValueError("Expected bounded nonempty text or null")


def validate(packet):
    required = {
        "scope", "invented", "contract_version", "snapshot_time",
        "admissions", "orders", "emar", "details",
    }
    if (
        not isinstance(packet, dict)
        or set(packet) != required
        or packet["scope"] != "SYNTHETIC"
        or packet["invented"] is not True
        or packet["contract_version"] != VERSION
    ):
        raise ValueError("Exact explicitly invented contract envelope required")
    snapshot = timestamp(packet["snapshot_time"])

    admissions = packet["admissions"]
    if not isinstance(admissions, list) or not admissions or len(admissions) > 500:
        raise ValueError("Bounded nonempty admission list required")
    admission_keys = set()
    for row in admissions:
        if (
            not isinstance(row, dict)
            or set(row) != {"scope", "subject_id", "hadm_id", "index_time"}
            or row["scope"] != "SYNTHETIC"
        ):
            raise ValueError("Exact invented admission schema required")
        _validate_identifier(row["subject_id"], nullable=False)
        _validate_identifier(row["hadm_id"], nullable=False)
        index_time = timestamp(row["index_time"])
        if index_time > snapshot:
            raise ValueError("Admission index_time cannot exceed packet snapshot")
        key = (row["subject_id"], row["hadm_id"])
        if key in admission_keys:
            raise ValueError("Admission subject/hadm key must be unique")
        admission_keys.add(key)

    schemas = {
        "orders": {
            "scope", "row_id", "source", "subject_id", "hadm_id",
            "pharmacy_id", "event_time", "available_time",
        },
        "emar": {
            "scope", "row_id", "subject_id", "hadm_id", "emar_id",
            "emar_seq", "event_time", "available_time", "status_text",
        },
        "details": {
            "scope", "row_id", "subject_id", "emar_id", "emar_seq",
            "event_time", "available_time",
        },
    }
    for name, expected_keys in schemas.items():
        rows = packet[name]
        if not isinstance(rows, list) or len(rows) > 5000:
            raise ValueError("Bounded record list required")
        row_ids = set()
        for row in rows:
            if (
                not isinstance(row, dict)
                or set(row) != expected_keys
                or row["scope"] != "SYNTHETIC"
            ):
                raise ValueError("Exact invented record schema required")
            _validate_text(row["row_id"], nullable=False, limit=100)
            if not row["row_id"].startswith("INVENTED-") or row["row_id"] in row_ids:
                raise ValueError("Unique invented row_id required")
            row_ids.add(row["row_id"])
            if "subject_id" in row:
                _validate_identifier(row["subject_id"], nullable=True)
            if "hadm_id" in row:
                _validate_identifier(row["hadm_id"], nullable=True)
            if "pharmacy_id" in row:
                _validate_text(row["pharmacy_id"], nullable=True, limit=100)
            if name == "orders" and row["source"] not in {"PRESCRIPTION", "PHARMACY"}:
                raise ValueError("Order source must be PRESCRIPTION or PHARMACY")
            if "emar_id" in row:
                _validate_text(row["emar_id"], nullable=True, limit=100)
            if "emar_seq" in row and (
                row["emar_seq"] is not None
                and (type(row["emar_seq"]) is not int or row["emar_seq"] < 0)
            ):
                raise ValueError("emar_seq must be a nonnegative integer or null")
            for field in ("event_time", "available_time"):
                _validate_optional_timestamp(row[field])
            if name == "emar":
                _validate_text(row["status_text"], nullable=True, allow_blank=True)

    emar_packet = {
        "scope": "SYNTHETIC",
        "invented": True,
        "parents": [
            {key: row[key] for key in ("scope", "row_id", "subject_id", "emar_id", "emar_seq")}
            for row in packet["emar"]
        ],
        "details": [
            {key: row[key] for key in ("scope", "row_id", "subject_id", "emar_id", "emar_seq")}
            for row in packet["details"]
        ],
    }
    validate_emar_linkage(emar_packet)


def _as_datetime(value):
    return timestamp(value) if value is not None else None


def _order_linkage_counts(connection):
    connection.execute("""
        CREATE TABLE prescriptions AS
        SELECT o.subject_id, o.hadm_id, o.pharmacy_id
        FROM orders o
        JOIN admissions a USING (subject_id, hadm_id)
        WHERE o.source = 'PRESCRIPTION'
          AND o.event_time IS NOT NULL
          AND o.available_time IS NOT NULL
          AND o.event_time <= a.index_time
          AND o.available_time <= a.index_time
    """)
    connection.execute("""
        CREATE TABLE pharmacy AS
        SELECT o.subject_id, o.hadm_id, o.pharmacy_id
        FROM orders o
        JOIN admissions a USING (subject_id, hadm_id)
        WHERE o.source = 'PHARMACY'
          AND o.event_time IS NOT NULL
          AND o.available_time IS NOT NULL
          AND o.event_time <= a.index_time
          AND o.available_time <= a.index_time
    """)
    template = ORDER_LINKAGE_SQL_PATH.read_text(encoding="utf-8")
    sql = template.format(
        keys="subject_id,hadm_id,pharmacy_id",
        complete=(
            "subject_id IS NOT NULL AND hadm_id IS NOT NULL "
            "AND pharmacy_id IS NOT NULL"
        ),
        rx_complete=(
            "rx.subject_id IS NOT NULL AND rx.hadm_id IS NOT NULL "
            "AND rx.pharmacy_id IS NOT NULL"
        ),
        join=(
            "rx.subject_id=p.subject_id AND rx.hadm_id=p.hadm_id "
            "AND rx.pharmacy_id=p.pharmacy_id"
        ),
    )
    return {state: count for state, count in connection.execute(sql).fetchall()}


def evaluate(packet):
    validate(packet)
    with duckdb.connect(":memory:") as connection:
        connection.execute("""
            CREATE TABLE admissions (
                scope VARCHAR, subject_id BIGINT, hadm_id BIGINT, index_time TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE orders (
                scope VARCHAR, row_id VARCHAR, source VARCHAR,
                subject_id BIGINT, hadm_id BIGINT, pharmacy_id VARCHAR,
                event_time TIMESTAMP, available_time TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE emar (
                scope VARCHAR, row_id VARCHAR, subject_id BIGINT, hadm_id BIGINT,
                emar_id VARCHAR, emar_seq BIGINT, event_time TIMESTAMP,
                available_time TIMESTAMP, status_text VARCHAR
            )
        """)
        connection.execute("""
            CREATE TABLE details (
                scope VARCHAR, row_id VARCHAR, subject_id BIGINT,
                emar_id VARCHAR, emar_seq BIGINT, event_time TIMESTAMP,
                available_time TIMESTAMP
            )
        """)
        for table, fields in (
            ("admissions", ("scope", "subject_id", "hadm_id", "index_time")),
            ("orders", (
                "scope", "row_id", "source", "subject_id", "hadm_id",
                "pharmacy_id", "event_time", "available_time",
            )),
            ("emar", (
                "scope", "row_id", "subject_id", "hadm_id", "emar_id",
                "emar_seq", "event_time", "available_time", "status_text",
            )),
            ("details", (
                "scope", "row_id", "subject_id", "emar_id", "emar_seq",
                "event_time", "available_time",
            )),
        ):
            rows = packet[table]
            if rows:
                values = [
                    [
                        _as_datetime(row[field])
                        if field in {"index_time", "event_time", "available_time"}
                        else row[field]
                        for field in fields
                    ]
                    for row in rows
                ]
                placeholders = ",".join("?" for _ in fields)
                connection.executemany(
                    f"INSERT INTO {table} VALUES ({placeholders})", values
                )

        query = (ROOT / "admission_medication_coverage_v1.sql").read_text(
            encoding="utf-8"
        )
        cursor = connection.execute(query)
        names = [column[0] for column in cursor.description]
        admissions = [dict(zip(names, row)) for row in cursor.fetchall()]
        linkage_sql = (
            ROOT / "admission_medication_linkage_counts_v1.sql"
        ).read_text(encoding="utf-8")
        states = connection.execute(
            linkage_sql,
            [packet["snapshot_time"]] * 4,
        ).fetchall()
        linkage = {state: count for state, count in states}
        visible_detail_count = connection.execute(
            """
            SELECT count(*)
            FROM details
            WHERE event_time IS NOT NULL
              AND available_time IS NOT NULL
              AND event_time <= CAST(? AS TIMESTAMP)
              AND available_time <= CAST(? AS TIMESTAMP)
            """,
            [packet["snapshot_time"]] * 2,
        ).fetchone()[0]
        order_linkage = _order_linkage_counts(connection)

    if len(admissions) != len(packet["admissions"]):
        raise AssertionError("Admission-level aggregation changed admission cardinality")
    if len({(row["subject_id"], row["hadm_id"]) for row in admissions}) != len(admissions):
        raise AssertionError("Admission output key is not unique")
    for row in admissions:
        if isinstance(row["index_time"], datetime):
            row["index_time"] = row["index_time"].strftime("%Y-%m-%d %H:%M:%S")
        if row["emar_record_rows"] != (
            row["emar_status_missing_rows"]
            + row["emar_status_present_uninterpreted_rows"]
        ):
            raise AssertionError("eMAR status evidence partition is not exhaustive")
        if row["administration_status_unknown_emar_rows"] != row["emar_record_rows"]:
            raise AssertionError("Unreviewed administration status must remain unknown")
    if sum(linkage.values()) != visible_detail_count:
        raise AssertionError("Detail linkage partition failed")
    return {
        "scope": "SYNTHETIC ONLY",
        "snapshot_time": packet["snapshot_time"],
        "admission_coverage": admissions,
        "detail_linkage_rows_as_of_snapshot": visible_detail_count,
        "detail_linkage_counts_as_of_snapshot": linkage,
        "order_pharmacy_linkage_counts_as_of_admission_index": {
            state: order_linkage.get(state, 0) for state in ORDER_LINKAGE_STATES
        },
        "clinical_gates": {
            "CLINICAL_ACCEPTANCE": "HOLD",
            "AKI_ENDPOINT_READY": False,
            "ML_TRAINING_PERMITTED": False,
        },
    }


def load_fixture():
    path = ROOT / "invented_admission_medication_fixture_v1.json"
    packet = json.loads(path.read_text(encoding="utf-8"))
    validate(packet)
    return packet
