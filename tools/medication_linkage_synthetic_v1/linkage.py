"""Synthetic-only linkage specification. No file readers or clinical inference."""
from collections import Counter, defaultdict
from datetime import datetime

KEYS = ('subject_id', 'hadm_id', 'pharmacy_id')
REQUIRED = set(KEYS) | {'starttime', 'stoptime'}
GATES = {'CLINICAL_ACCEPTANCE': 'HOLD', 'AKI_ENDPOINT_READY': False,
         'ML_TRAINING_PERMITTED': False}


def key(row):
    values = tuple(str(row[k]).strip() if row[k] is not None else '' for k in KEYS)
    return values if all(values) else None


def interval(row):
    values = [row['starttime'], row['stoptime']]
    missing = [v is None or str(v).strip() == '' for v in values]
    if all(missing):
        return 'both_missing', None
    if missing[0]:
        return 'start_missing', None
    if missing[1]:
        return 'stop_missing', None
    try:
        a, b = [datetime.fromisoformat(str(v)) for v in values]
        if a.tzinfo is not None or b.tzinfo is not None:
            return 'invalid_timestamp', None
    except (TypeError, ValueError):
        return 'invalid_timestamp', None
    if b < a:
        return 'negative', None
    if b == a:
        return 'zero', None
    return 'positive', (a, b)


def audit(prescriptions, pharmacy, *, synthetic=False):
    """Return aggregate QC counts only; require explicit synthetic attestation.

    Each prescription contributes exactly one linkage category. Duplicate Pharmacy
    keys remain ambiguous even if their contents are identical. Time overlap uses
    half-open positive intervals; touching endpoints do not overlap. Overlap is
    documentary concordance only, never evidence of drug administration.
    """
    if synthetic is not True:
        raise ValueError('This prototype is authorized for synthetic fixtures only')
    for rows in (prescriptions, pharmacy):
        if not isinstance(rows, (list, tuple)):
            raise TypeError('Use in-memory synthetic sequences')
        for row in rows:
            if not isinstance(row, dict) or not REQUIRED.issubset(row):
                raise ValueError('Missing required synthetic schema fields')
            if any(row[k] is not None and not isinstance(row[k], str) for k in REQUIRED):
                raise TypeError('Synthetic schema values must be strings or None')
    index = defaultdict(list)
    pharmacy_ids = set()
    for row in pharmacy:
        k = key(row)
        if k:
            index[k].append(row)
        pid = (row['pharmacy_id'] or '').strip()
        if pid:
            pharmacy_ids.add(pid)
    link, temporal = Counter(), Counter()
    for row in prescriptions:
        k = key(row)
        matches = index.get(k, []) if k else []
        if not k:
            link['missing_identity_key'] += 1
        elif len(matches) > 1:
            link['ambiguous_duplicate_key'] += 1
        elif not matches:
            category = 'pharmacy_id_present_identity_discordant' if k[2] in pharmacy_ids else 'unmatched'
            link[category] += 1
        else:
            link['unique_three_key_candidate'] += 1
            pa, a = interval(row)
            pb, b = interval(matches[0])
            if a is None or b is None:
                temporal['not_evaluable'] += 1
            else:
                temporal['overlap' if max(a[0], b[0]) < min(a[1], b[1]) else 'nonoverlap'] += 1
    assert sum(link.values()) == len(prescriptions)
    assert sum(temporal.values()) == link['unique_three_key_candidate']
    return {
        'label': 'PRELIMINARY — NOT CLINICALLY ADJUDICATED',
        'scope': 'SYNTHETIC ONLY', **GATES,
        'prescription_rows': len(prescriptions), 'pharmacy_rows': len(pharmacy),
        'duplicate_pharmacy_key_groups': sum(len(v) > 1 for v in index.values()),
        'duplicate_prescription_key_groups': sum(n > 1 for n in Counter(key(r) for r in prescriptions if key(r)).values()),
        'pharmacy_rows_missing_identity_key': sum(key(r) is None for r in pharmacy),
        'linkage': dict(sorted(link.items())), 'unique_candidate_temporal': dict(sorted(temporal.items())),
        'timestamp_partitions': {name: dict(sorted(Counter(interval(r)[0] for r in rows).items()))
                                 for name, rows in [('prescriptions', prescriptions), ('pharmacy', pharmacy)]},
    }
