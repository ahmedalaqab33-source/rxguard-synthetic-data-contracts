"""Synthetic-only temporal comparison kernel; not an AKI phenotype or raw-data reader."""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
GATES={'CLINICAL_ACCEPTANCE':'HOLD','AKI_ENDPOINT_READY':False,'ML_TRAINING_PERMITTED':False}
def comparison(earlier_time, earlier_value, current_time, current_value, unit='mg/dL'):
    result={'status':'NOT_EVALUABLE','absolute_48h':False,'ratio_7d':False,'gates':dict(GATES)}
    if unit != 'mg/dL':
        return {**result,'reason':'UNIT_REQUIRES_REVIEWED_CONVERSION'}
    if not isinstance(earlier_time,datetime) or not isinstance(current_time,datetime):
        return {**result,'reason':'MISSING_OR_INVALID_TIME'}
    try:
        elapsed=current_time-earlier_time
    except TypeError:
        return {**result,'reason':'INCONSISTENT_TIMEZONE'}
    try:
        old,new=Decimal(str(earlier_value)),Decimal(str(current_value))
        if not old.is_finite() or not new.is_finite() or old<=0 or new<=0:
            raise ValueError('invalid value')
    except (InvalidOperation,ValueError):
        return {**result,'reason':'MISSING_OR_INVALID_VALUE'}
    if elapsed<=timedelta(0):
        return {**result,'reason':'REFERENCE_NOT_STRICTLY_EARLIER'}
    return {**result,'status':'COMPARISON_ONLY','reason':'NO_CLINICAL_CLASSIFICATION',
        'absolute_48h':elapsed<=timedelta(hours=48) and new-old>=Decimal('0.3'),
        'ratio_7d':elapsed<=timedelta(days=7) and new>=old*Decimal('1.5')}
