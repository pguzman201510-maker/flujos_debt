import pandas as pd
from datetime import date
import logging

logger = logging.getLogger(__name__)

def compute_day_count(start_date, end_date, method_code):
    """
    Computes days and factor based on day count convention.
    Known method codes from 'METODO CONTEO' based on context (often mapped to integers):
    0: Actual/360
    1: Actual/365 Base fija
    2: Actual/365
    3: Actual/365 Ajustado
    4: 30E/360 europeo
    5: Unknown / fallback
    We'll interpret codes as well as string names.
    Returns: (days, factor)
    """
    if pd.isna(start_date) or pd.isna(end_date):
        return 0, 0.0

    s = start_date if isinstance(start_date, pd.Timestamp) else pd.to_datetime(start_date)
    e = end_date if isinstance(end_date, pd.Timestamp) else pd.to_datetime(end_date)

    if s >= e:
        return 0, 0.0

    actual_days = (e - s).days
    code = str(method_code).strip().upper()

    days = actual_days
    factor = 0.0

    if code == '0' or 'ACTUAL/360' in code:
        factor = days / 360.0
    elif code == '1' or 'BASE FIJA' in code:
        # Actual/365 Base Fija usually implies dividing strictly by 365
        factor = days / 365.0
    elif code == '2' or code == '3' or 'ACTUAL/365' in code:
        # Actual/365 - sometimes accounts for leaps but dividing by 365 is standard "Actual/365 Fixed"
        # For simplicity, we just divide by 365
        factor = days / 365.0
    elif code == '4' or '30E/360' in code:
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
