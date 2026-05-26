import pandas as pd
import logging
from config.settings import FIXED_RATE_CODES, MBID_RATE
from modules.forward_rates import get_forward_rate

logger = logging.getLogger(__name__)

def calculate_interest_flow(interest_dates, df_amortization_flow, row_oracle, row_inv, row_guias, df_tasas, compute_day_count, shock_int=0.0):
    """
    Computes interest payments for each period in the standalone interest flow.
    interest_dates: list of pd.Timestamp
    df_amortization_flow: DataFrame containing 'fecha_operacion', 'saldo_insoluto'.
    row_oracle: contains CLASE_INT, MARGEN_VALOR, SDO_US
    row_inv: contains accurate unrounded MARGEN VALOR
    row_guias: contains METODO CONTEO, FECHA INICIAL INTERES
    df_tasas: DataFrame for forward rates.
    compute_day_count: callable function compute_day_count(start_date, end_date, method) -> (days, factor)
    """
    if not interest_dates:
        return pd.DataFrame()

    clase_int = str(row_oracle.get('CLASE_INT', '')).strip()

    margen = 0.0

    # Try Inventario MARGEN VALOR first (high precision decimal)
    val_inv = row_inv.get('MARGEN VALOR') if row_inv is not None else None
    if not pd.isna(val_inv) and str(val_inv).strip() != '' and str(val_inv).strip().upper() != 'GUIA':
        try:
            margen = float(val_inv)
        except:
            pass

    # If GUIA or missing, try Guias MARGEN VALOR
    if margen == 0.0 and row_guias is not None and 'MARGEN VALOR' in row_guias:
        val_guias = row_guias.get('MARGEN VALOR')
        if not pd.isna(val_guias) and str(val_guias).strip() != '':
            try:
                margen = float(val_guias)
            except:
                pass

    # Fallback to Oracle
    if margen == 0.0:
        try:
            val_or = row_oracle.get('MARGEN_VALOR', 0.0)
            if not pd.isna(val_or) and str(val_or).strip() != '':
                m = float(val_or)
                # Oracle margin might be in percentages like 4.8 instead of 0.048
                margen = m / 100.0 if m > 1 else m
                margen = margen / 100.0 if margen > 0.5 else margen
        except:
            margen = 0.0

    metodo_conteo = row_guias.get('METODO CONTEO') if row_guias is not None else None

    try:
        initial_balance = float(row_oracle.get('SDO_US', 0))
    except:
        initial_balance = 0.0

    # Determine the step in months for fallback if start_date needs adjustment
    from dateutil.relativedelta import relativedelta
    periodicity = str(row_guias.get('PERIODICIDAD PAGO INTERESES')).strip().upper() if row_guias is not None else '6'
    if periodicity == 'GUIA':
        periodicity = str(row_guias.get('MES PERIODICIDAD')).strip()
    try:
        p = float(periodicity)
    except:
        p = 6
    months_step = 12 if p == 1 else (6 if p == 2 else (1 if p == 12 else (int(p) if p > 0 else 6)))

    # Start date of accrual
    start_date = pd.to_datetime(row_guias.get('FECHA INICIAL INTERES'), errors='coerce', dayfirst=True) if row_guias is not None else None
    if pd.isna(start_date):
        # Fallback to some date if missing
        start_date = interest_dates[0] - pd.DateOffset(months=months_step)

    # If the first interest date in our list is far ahead of start_date (because earlier ones were filtered by cutoff)
    # the accrual should only be from the previous periodicity, not from the very beginning.
    # While start_date + N*periodicity < interest_dates[0]... advance it.
    first_payment = interest_dates[0]
    curr = start_date
    while curr + relativedelta(months=months_step) <= first_payment:
        # Don't advance if the exact step lands on first payment, we want accrual start to be strictly before
        if curr + relativedelta(months=months_step) == first_payment:
            curr += relativedelta(months=months_step)
            break
        curr += relativedelta(months=months_step)

    # But we want the start of the accrual period FOR the first payment, which is one step before
    if curr == first_payment:
        start_date = curr - relativedelta(months=months_step)
    else:
        # In case it didn't align perfectly, just take the max of start_date or first_payment - step
        inferred_start = first_payment - relativedelta(months=months_step)
        start_date = max(start_date, inferred_start)

    # Helper to get outstanding balance AT a specific date
    def get_balance_at(date):
        if df_amortization_flow.empty:
            return initial_balance
        # Balance is initial_balance minus all amortizations strictly before or equal to this date?
        # Actually, interest for a period [t1, t2] accrues on the balance during that period.
        # Amortizations exactly ON t2 don't reduce the balance FOR the period [t1, t2], but FOR [t2, t3].
        # So we want the balance immediately after t1 (which is the start of the accrual).
        # We find the latest amortization that happened ON OR BEFORE `date`
        past_amortizations = df_amortization_flow[df_amortization_flow['fecha_operacion'] <= date]
        if past_amortizations.empty:
            return initial_balance
        return past_amortizations.iloc[-1]['saldo_insoluto']

    flow = []

    current_start = start_date
    for current_date in interest_dates:
        # MBID/BIRF Specific Logic
        pmista = str(row_oracle.get('PMISTA', '')).strip().upper()

        is_fixed = clase_int in FIXED_RATE_CODES

        # Base annual rate components
        spread_premium = 0.0
        forward_val = 0.0

        if is_fixed:
            base_annual_rate = margen
        else:
            # Variable rate
            index_col = clase_int

            if pmista == 'BIRF':
                # Calculate maturity in years from PRIM_PAGO to ULT_PAGO
                prim_pago = pd.to_datetime(row_oracle.get('PRIM_PAGO'), errors='coerce')
                ult_pago = pd.to_datetime(row_oracle.get('ULT_PAGO'), errors='coerce')
                years = 0.0
                if not pd.isna(prim_pago) and not pd.isna(ult_pago) and ult_pago >= prim_pago:
                    years = (ult_pago - prim_pago).days / 365.25

                if clase_int == 'UBIR':
                    index_col = 'TSO6'
                    if years < 7: spread_premium = 0.0075
                    elif years <= 8: spread_premium = 0.0105
                    elif years <= 12: spread_premium = 0.0120
                    elif years <= 15: spread_premium = 0.0135
                    elif years <= 18: spread_premium = 0.0150
                    else: spread_premium = 0.0165
                elif clase_int == 'EBIR':
                    index_col = 'EUL6'
                    if years < 7: spread_premium = 0.0061
                    elif years <= 8: spread_premium = 0.0071
                    elif years <= 12: spread_premium = 0.0086
                    elif years <= 15: spread_premium = 0.0101
                    elif years <= 18: spread_premium = 0.0116
                    else: spread_premium = 0.0131

            forward_val = get_forward_rate(df_tasas, index_col, current_date) / 100.0
            base_annual_rate = forward_val + spread_premium + margen

        # Add Annual MBID margin (Only for variable rates per user instruction)
        if pmista == 'BID' and not is_fixed:
            base_annual_rate += MBID_RATE

        # Add Annual shock
        if shock_int != 0.0:
            base_annual_rate += (shock_int / 100.0)

        # Day count or Frequency division
        if current_start >= current_date:
            current_start = current_date - pd.DateOffset(months=6)

        if not is_fixed:
            # User instruction: divide nominal variable rate by the frequency
            frequency = float(p) if p > 0 else 1.0
            factor = 1.0 / frequency
        else:
            # Fixed rates continue using standard Day Count Conventions
            _, factor = compute_day_count(current_start, current_date, metodo_conteo)

        rate = base_annual_rate

        # Balance used is the balance at `current_start`
        balance = get_balance_at(current_start)

        interes = balance * rate * factor
        flow.append({
            'fecha_operacion': current_date,
            'pago_interes': max(0, interes),
            'tasa_aplicada': rate
        })

        # Advance
        current_start = current_date

    return pd.DataFrame(flow)
