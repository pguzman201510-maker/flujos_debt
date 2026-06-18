import pandas as pd
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)

def generate_calendar(row, df_tabla_nd, cutoff_date):
    """
    Generates a list of payment dates for a credit based on its periodicity.
    cutoff_date: pandas Timestamp or string (e.g. "2026-04-30")
    row: Must contain 'PRIM_PAGO', 'ULT_PAGO', 'TIPO AMORTIZACION', 'ID_CREDITO'
    df_tabla_nd: DataFrame with 'ID Crédito' and 'Vencimiento'
    Returns (dates, error_type)
    """
    try:
        cutoff = pd.to_datetime(cutoff_date)
    except Exception as e:
        logger.error(f"Invalid cutoff_date: {e}")
        return [], None

    # Get basic dates
    prim_pago = pd.to_datetime(row.get('PRIM_PAGO'), errors='coerce')
    ult_pago = pd.to_datetime(row.get('ULT_PAGO'), errors='coerce')
    periodicity = row.get('TIPO AMORTIZACION')
    credito_id = row.get('ID_CREDITO')

    error_type = None

    # Bullet check: missing dates, or ULT_PAGO <= PRIM_PAGO
    is_bullet = False
    if pd.isna(prim_pago) or pd.isna(ult_pago):
        is_bullet = True

    if not is_bullet and ult_pago < prim_pago:
        is_bullet = True
        error_type = "FECHAS_INCORRECTAS" # ULT_PAGO < PRIM_PAGO

    if not is_bullet and prim_pago == ult_pago:
        is_bullet = True

    p_str = str(periodicity).strip().upper()
    is_empty_per = (p_str == 'NAN' or p_str == 'NONE' or p_str == '')

    # Fallback for empty periodicity when it's not a bullet
    if not is_bullet:
        if is_empty_per:
            # New rule: if empty and not bullet, check tabla_nd first
            if df_tabla_nd is not None and not df_tabla_nd.empty and (df_tabla_nd['ID Crédito'].astype(str) == str(credito_id)).any():
                periodicity = 'ND'
            else:
                # Fallback to interest periodicity or report error
                int_per = str(row.get('PERIODICIDAD PAGO INTERESES', '')).strip().upper()
                if int_per == 'GUIA':
                    periodicity = str(row.get('MES PERIODICIDAD', '')).strip()
                elif int_per != 'NAN' and int_per != 'NONE' and int_per != '':
                    periodicity = int_per

                # If still empty or 0, it's an error
                if str(periodicity).strip().upper() in ['NAN', 'NONE', '', '0']:
                    error_type = "AMORTIZACION_VACIA_NO_BULLET"
        elif p_str == 'ND':
            # Fallback if ND is not found in tabla_nd
            if df_tabla_nd is None or df_tabla_nd.empty or not (df_tabla_nd['ID Crédito'].astype(str) == str(credito_id)).any():
                error_type = "ND_NO_ENCONTRADO"
                periodicity = 2 # Hard fallback to semiannual

    dates = []

    if is_bullet:
        # For bullet, the single payment date is the ultimate date (or fallback if missing)
        # If both missing, it's problematic, we just return empty or fallback
        if not pd.isna(ult_pago):
            dates.append(ult_pago)
        elif not pd.isna(prim_pago):
            dates.append(prim_pago)
    elif str(periodicity).strip().upper() == 'ND':
        # Lookup in tabla ND (we know it exists because of the fallback above)
        nd_rows = df_tabla_nd[df_tabla_nd['ID Crédito'].astype(str) == str(credito_id)]
        try:
            def parse_nd_date(d):
                if isinstance(d, (int, float)):
                    return pd.to_datetime(d, unit='D', origin='1899-12-30')
                return pd.to_datetime(d, errors='coerce')

            nd_dates = nd_rows['Vencimiento'].apply(parse_nd_date).dropna().tolist()
            dates.extend(nd_dates)
        except Exception as e:
            logger.error(f"Credit {credito_id}: Error parsing ND dates: {e}")
    else:
        # Standard periodicities
        try:
            p = float(periodicity)
        except:
            p = 0

        months_step = 0
        if p == 1:
            months_step = 12
        elif p == 2:
            months_step = 6
        elif p == 12:
            months_step = 1
        else:
            logger.warning(f"Credit {credito_id}: Unknown periodicity {periodicity}. Assuming BULLET at ULT_PAGO.")
            if not pd.isna(ult_pago):
                dates.append(ult_pago)

        if months_step > 0:
            current = prim_pago
            while current <= ult_pago:
                dates.append(current)
                current += relativedelta(months=months_step)

            # Ensure ult_pago is exactly included if it was slightly off
            if dates and dates[-1] < ult_pago:
                if dates[-1].year == ult_pago.year and dates[-1].month == ult_pago.month:
                    pass # Ignore ult_pago if the scheduled date is already in the same month
                else:
                    dates.append(ult_pago)

    # Filter dates > cutoff_date strictly
    valid_dates = [d for d in dates if d > cutoff]

    # Sort dates just in case
    valid_dates.sort()

    return valid_dates, error_type

def generate_interest_calendar(combined_row, cutoff_date, amort_dates=None):
    """
    Generates a list of interest payment dates based on combined_row.
    combined_row: Must contain 'FECHA INICIAL INTERES', 'FECHA FINAL INTERES',
                  'PERIODICIDAD PAGO INTERESES', 'MES PERIODICIDAD'
    amort_dates: Optional list of amortization dates. If provided, interest dates
                 will natively align to their day/month combinations by stepping from them.
    """
    try:
        cutoff = pd.to_datetime(cutoff_date)
    except Exception as e:
        logger.error(f"Invalid cutoff_date: {e}")
        return []

    if combined_row is None or (isinstance(combined_row, (pd.DataFrame, pd.Series)) and combined_row.empty):
        return []

    start_date = pd.to_datetime(combined_row.get('FECHA INICIAL INTERES'), errors='coerce', dayfirst=True)
    end_date = pd.to_datetime(combined_row.get('FECHA FINAL INTERES'), errors='coerce', dayfirst=True)
    periodicity = str(combined_row.get('PERIODICIDAD PAGO INTERESES')).strip().upper()
    credito_id = combined_row.get('ID_CREDITO', 'Unknown')

    if pd.isna(start_date) or pd.isna(end_date) or start_date > end_date:
        return []

    if periodicity == 'GUIA':
        periodicity = str(combined_row.get('MES PERIODICIDAD')).strip()

    try:
        p = float(periodicity)
    except:
        p = 0

    months_step = 0
    if p == 1:
        months_step = 12
    elif p == 2:
        months_step = 6
    elif p == 12:
        months_step = 1
    elif p > 0:
        months_step = int(p)
    else:
        logger.warning(f"Credit {credito_id}: Unknown interest periodicity {periodicity}. Assuming BULLET at end_date.")
        valid_dates = [end_date] if end_date > cutoff else []
        return valid_dates

    dates_set = set()
    if months_step > 0:
        if amort_dates and len(amort_dates) > 0:
            # Use the first amortization date as the alignment seed
            seed = amort_dates[0]

            # Step backwards to cover the period before amortization starts (down to start_date)
            curr = seed
            while curr >= start_date:
                dates_set.add(curr)
                curr -= relativedelta(months=months_step)

            # Step forwards to cover the remaining period (up to end_date)
            curr = seed
            while curr <= end_date:
                dates_set.add(curr)
                curr += relativedelta(months=months_step)
        else:
            # Fallback if no amortization dates are available to sync to
            curr = start_date
            while curr <= end_date:
                dates_set.add(curr)
                curr += relativedelta(months=months_step)

        # Handle appending the ultimate end_date if it wasn't perfectly reached
        dates = sorted(list(dates_set))
        if not dates:
             dates.append(end_date)
        elif dates[-1] < end_date:
            if dates[-1].year == end_date.year and dates[-1].month == end_date.month:
                pass # Ignore end_date if the scheduled date is already in the same month
            else:
                dates.append(end_date)
    else:
        dates = sorted(list(dates_set))

    valid_dates = [d for d in dates if d > cutoff]
    valid_dates.sort()
    return valid_dates
