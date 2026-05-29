import pandas as pd
from datetime import date
import logging

logger = logging.getLogger(__name__)

def compute_day_count(start_date, end_date, method_code):
    """
    Computes days and factor based on day count convention.
    Known method codes from 'METODO CONTEO' based on user definitions:
    0: 30/360 (US)
    1: 365/365
    2: actual/360
    3: actual/365
    4: actual/365 adjusted
    5: 30E/360
    Returns: (days, factor)
    """
    if pd.isna(start_date) or pd.isna(end_date):
        return 0, 0.0

    s = start_date if isinstance(start_date, pd.Timestamp) else pd.to_datetime(start_date)
    e = end_date if isinstance(end_date, pd.Timestamp) else pd.to_datetime(end_date)

    if s >= e:
        return 0, 0.0

    actual_days = (e - s).days
    try:
        code = str(int(float(method_code)))
    except:
        code = str(method_code).strip().upper()

    days = actual_days
    factor = 0.0

    if code == '0' or '30/360' in code:
        # 30/360 US
        d1 = s.day
        d2 = e.day
        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 == 30:
            d2 = 30
        days = (e.year - s.year) * 360 + (e.month - s.month) * 30 + (d2 - d1)
        factor = days / 360.0

    elif code in ['1', '3', '4'] or '365' in code:
        # 365/365, actual/365, actual/365 adjusted -> Base 365
        factor = days / 365.0

    elif code == '2' or 'ACTUAL/360' in code:
        # Actual / 360
        factor = days / 360.0

    elif code == '5' or '30E/360' in code:
        # 30E/360 European
        d1 = s.day
        d2 = e.day
        if d1 == 31: d1 = 30
        if d2 == 31: d2 = 30
        days = (e.year - s.year) * 360 + (e.month - s.month) * 30 + (d2 - d1)
        factor = days / 360.0

    else:
        # Fallback to Actual/360
        factor = days / 360.0

    return days, factor
