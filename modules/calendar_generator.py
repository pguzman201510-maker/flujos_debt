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
    """
    try:
        cutoff = pd.to_datetime(cutoff_date)
    except Exception as e:
        logger.error(f"Invalid cutoff_date: {e}")
        return []

    # Get basic dates
    prim_pago = pd.to_datetime(row.get('PRIM_PAGO'), errors='coerce')
    ult_pago = pd.to_datetime(row.get('ULT_PAGO'), errors='coerce')
    periodicity = row.get('TIPO AMORTIZACION')
    credito_id = row.get('ID_CREDITO')

    # Bullet check: missing dates, or ULT_PAGO <= PRIM_PAGO
    is_bullet = False
    if pd.isna(prim_pago) or pd.isna(ult_pago):
        is_bullet = True
        logger.warning(f"Credit {credito_id}: Missing dates. Assuming BULLET.")

    if not is_bullet and ult_pago < prim_pago:
        is_bullet = True
        logger.warning(f"Credit {credito_id}: ULT_PAGO ({ult_pago.date()}) < PRIM_PAGO ({prim_pago.date()}). Assuming BULLET.")

    if not is_bullet and prim_pago == ult_pago:
        is_bullet = True

    dates = []

    if is_bullet:
        # For bullet, the single payment date is the ultimate date (or fallback if missing)
        # If both missing, it's problematic, we just return empty or fallback
        if not pd.isna(ult_pago):
            dates.append(ult_pago)
        elif not pd.isna(prim_pago):
            dates.append(prim_pago)
    elif str(periodicity).strip().upper() == 'ND':
        # Lookup in tabla ND
        if df_tabla_nd is not None and not df_tabla_nd.empty:
            nd_rows = df_tabla_nd[df_tabla_nd['ID Crédito'].astype(str) == str(credito_id)]
            if not nd_rows.empty:
                # Convert Excel serial dates or normal dates
                try:
                    # In excel, 40000 etc are serial dates
                    # pd.to_datetime with unit 'D' and origin '1899-12-30' handles excel dates
                    def parse_nd_date(d):
                        if isinstance(d, (int, float)):
                            return pd.to_datetime(d, unit='D', origin='1899-12-30')
                        return pd.to_datetime(d, errors='coerce')

                    nd_dates = nd_rows['Vencimiento'].apply(parse_nd_date).dropna().tolist()
                    dates.extend(nd_dates)
                except Exception as e:
                    logger.error(f"Credit {credito_id}: Error parsing ND dates: {e}")
            else:
                logger.warning(f"Credit {credito_id}: Type ND but not found in tabla ND. Assuming BULLET at ULT_PAGO.")
                if not pd.isna(ult_pago):
                    dates.append(ult_pago)
        else:
            if not pd.isna(ult_pago):
                dates.append(ult_pago)
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

            # Ensure ult_pago is exactly included if it was slightly off,
            # but usually it's exact in financial structures
            if dates and dates[-1] < ult_pago:
                 dates.append(ult_pago)

    # Filter dates > cutoff_date strictly
    valid_dates = [d for d in dates if d > cutoff]

    # Sort dates just in case
    valid_dates.sort()

    return valid_dates

def generate_interest_calendar(combined_row, cutoff_date):
    """
    Generates a list of interest payment dates based on combined_row.
    combined_row: Must contain 'FECHA INICIAL INTERES', 'FECHA FINAL INTERES',
                  'PERIODICIDAD PAGO INTERESES', 'MES PERIODICIDAD'
    """
    try:
        cutoff = pd.to_datetime(cutoff_date)
    except Exception as e:
        logger.error(f"Invalid cutoff_date: {e}")
        return []

    if combined_row is None or (isinstance(combined_row, (pd.DataFrame, pd.Series)) and combined_row.empty):
        return []

    start_date = pd.to_datetime(combined_row.get('FECHA INICIAL INTERES'), errors='coerce')
    end_date = pd.to_datetime(combined_row.get('FECHA FINAL INTERES'), errors='coerce')
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

    dates = []
    if months_step > 0:
        current = start_date
        # FECHA INICIAL INTERES is actually the first payment date
        while current <= end_date:
            dates.append(current)
            current += relativedelta(months=months_step)

        if not dates or dates[-1] < end_date:
             dates.append(end_date)

    valid_dates = [d for d in dates if d > cutoff]
    valid_dates.sort()
    return valid_dates
