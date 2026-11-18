"""Synthetic evidence trace checks. No source readers or clinical decisions."""
from datetime import datetime

GATES = {'CLINICAL_ACCEPTANCE': 'HOLD', 'AKI_ENDPOINT_READY': False,
         'ML_TRAINING_PERMITTED': False}

def assess_trace(trace, *, synthetic=False):
    if synthetic is not True or trace.get('scope') != 'SYNTHETIC':
        raise ValueError('Synthetic fixtures only')
    fields = ('evidence_id', 'source_locator', 'source_digest', 'policy_version',
              'event_time', 'available_time', 'decision_time', 'release_status')
    if any(not trace.get(k) for k in fields):
        raise ValueError('Incomplete evidence trace')
    digest = trace['source_digest']
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Expected SHA-256 shape; authenticity is not inferred')
    times = [datetime.fromisoformat(trace[k]) for k in
             ('event_time', 'available_time', 'decision_time')]
    if any(t.tzinfo is None or t.utcoffset() is None for t in times):
        raise ValueError('Explicit timezones required')
    reasons = []
    if times[0] > times[2]: reasons.append('FUTURE_EVENT')
    if times[1] > times[2]: reasons.append('NOT_YET_AVAILABLE')
    if trace['release_status'] != 'SYNTHETIC_ACCEPTED':
        reasons.append('UNACCEPTED_SOURCE_ASSERTION')
    return {'scope': 'SYNTHETIC', 'trace_eligible': not reasons,
            'reasons': reasons, 'gates': dict(GATES)}
