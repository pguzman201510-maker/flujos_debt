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
    row_guias: can be a Series or a DataFrame with columns METODO CONTEO, FECHA INICIAL INTERES, FECHA FINAL INTERES, TASA INTERES, MARGEN VALOR
    df_tasas: DataFrame for forward rates.
    compute_day_count: callable function compute_day_count(start_date, end_date, method) -> (days, factor)
    """
    if not interest_dates:
        return pd.DataFrame()

    def get_active_guide(date):
        if not isinstance(row_guias, pd.DataFrame) or row_guias.empty:
            return row_guias

        # Look for a guide where date falls between FECHA INICIAL INTERES and FECHA FINAL INTERES
        # Using pre-converted columns from main.py
        mask = (row_guias['FECHA INICIAL INTERES_DT'] <= date) & (date <= row_guias['FECHA FINAL INTERES_DT'])
        active = row_guias[mask]

        if not active.empty:
            return active.iloc[0]

        # Fallback to the most recent guide if none found for this date
        return row_guias.iloc[-1]

    # Use representative guide for initial parameters
    if isinstance(row_guias, pd.DataFrame) and not row_guias.empty:
        guide_rep = row_guias.iloc[-1] # default to most recent
    else:
        guide_rep = row_guias

    metodo_conteo_rep = guide_rep.get('METODO CONTEO') if guide_rep is not None else None

    try:
        initial_balance = float(row_oracle.get('SDO_US', 0))
    except:
        initial_balance = 0.0

    # Determine the step in months for fallback if start_date needs adjustment
    from dateutil.relativedelta import relativedelta

    periodicity_rep = '6'
    if row_inv is not None and 'PERIODICIDAD PAGO INTERESES' in row_inv:
        val_per = row_inv.get('PERIODICIDAD PAGO INTERESES')
        if pd.notna(val_per) and str(val_per).strip() != '':
            periodicity_rep = str(val_per).strip().upper()

    if periodicity_rep == 'GUIA' and guide_rep is not None:
        periodicity_rep = str(guide_rep.get('MES PERIODICIDAD', '6')).strip()

    try:
        p_rep = float(periodicity_rep)
    except:
        p_rep = 6
    months_step_rep = 12 if p_rep == 1 else (6 if p_rep == 2 else (1 if p_rep == 12 else (int(p_rep) if p_rep > 0 else 6)))

    # Start date of accrual
    start_date = pd.to_datetime(guide_rep.get('FECHA INICIAL INTERES'), errors='coerce', dayfirst=True) if guide_rep is not None else None
    if pd.isna(start_date):
        # Fallback to some date if missing
        start_date = interest_dates[0] - pd.DateOffset(months=months_step_rep)

    # If the first interest date in our list is far ahead of start_date (because earlier ones were filtered by cutoff)
    # the accrual should only be from the previous periodicity, not from the very beginning.
    # While start_date + N*periodicity < interest_dates[0]... advance it.
    first_payment = interest_dates[0]
    curr = start_date
    while curr + relativedelta(months=months_step_rep) <= first_payment:
        # Don't advance if the exact step lands on first payment, we want accrual start to be strictly before
        if curr + relativedelta(months=months_step_rep) == first_payment:
            curr += relativedelta(months=months_step_rep)
            break
        curr += relativedelta(months=months_step_rep)

    # But we want the start of the accrual period FOR the first payment, which is one step before
    if curr == first_payment:
        start_date = curr - relativedelta(months=months_step_rep)
    else:
        # In case it didn't align perfectly, just take the max of start_date or first_payment - step
        inferred_start = first_payment - relativedelta(months=months_step_rep)
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
        # Dynamic active guide lookup
        active_guide = get_active_guide(current_date)

        # 1. Determine Rate Type (clase_int)
        # Prioritize TASA INTERES from Guide
        clase_int = str(active_guide.get('TASA INTERES', '')).strip() if active_guide is not None else ''
        if not clase_int or clase_int.upper() == 'NAN':
            clase_int = str(row_oracle.get('CLASE_INT', '')).strip()

        # 2. Determine Margin
        margen = 0.0
        # Try Inventario MARGEN VALOR first (high precision decimal)
        val_inv = row_inv.get('MARGEN VALOR') if row_inv is not None else None
        if not pd.isna(val_inv) and str(val_inv).strip() != '' and str(val_inv).strip().upper() != 'GUIA':
            try:
                margen = float(val_inv)
            except:
                pass

        # If GUIA or missing, try Guias MARGEN VALOR
        if margen == 0.0 and active_guide is not None and 'MARGEN VALOR' in active_guide:
            val_guias = active_guide.get('MARGEN VALOR')
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

        # 3. Determine Method/Periodicity
        metodo_conteo = active_guide.get('METODO CONTEO') if active_guide is not None else metodo_conteo_rep

        periodicity = '6'
        if row_inv is not None and 'PERIODICIDAD PAGO INTERESES' in row_inv:
            val_per = row_inv.get('PERIODICIDAD PAGO INTERESES')
            if pd.notna(val_per) and str(val_per).strip() != '':
                periodicity = str(val_per).strip().upper()

        if periodicity == 'GUIA' and active_guide is not None:
            periodicity = str(active_guide.get('MES PERIODICIDAD', '6')).strip()

        try:
            p = float(periodicity)
        except:
            p = 6

        # MBID/BIRF Specific Logic
        pmista = str(row_oracle.get('PMISTA', '')).strip().upper()

        # Re-evaluate rate type based on dynamic clase_int
        is_fixed = clase_int in FIXED_RATE_CODES

        # Base annual rate components
        spread_premium = 0.0
        forward_val = 0.0

        if is_fixed:
            base_annual_rate = margen
        else:
            # Variable rate
            index_col = clase_int
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

        # Balance used is the balance at `current_start`
        balance = get_balance_at(current_start)

        interes = balance * base_annual_rate * factor

        # User requested tasa_aplicada to be the periodic rate for variable interests
        # for easier verification against manual calculations
        if not is_fixed:
            applied_rate_report = base_annual_rate * factor
        else:
            applied_rate_report = base_annual_rate

        flow.append({
            'fecha_operacion': current_date,
            'pago_interes': max(0, interes),
            'tasa_aplicada': applied_rate_report,
            'clase_int_periodo': clase_int,
            'margen_aplicado': margen,
            'valor_indice': forward_val
        })

        # Advance
        current_start = current_date

    return pd.DataFrame(flow)
