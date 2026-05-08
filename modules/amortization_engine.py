import pandas as pd
import logging

logger = logging.getLogger(__name__)

def build_amortization_flow(row, dates, df_tabla_nd):
    """
    Distributes SALDO_PAGO (or SDO_US fallback) across the dates.
    For ND, uses % Real from df_tabla_nd if available.
    Otherwise, divides equally or completely at the end (bullet).
    """
    # Prefer SALDO_PAGO / SALDO_REAL which is the true balance in currency
    sdo_us = row.get('SALDO_PAGO')
    if pd.isna(sdo_us) or sdo_us == 0:
        sdo_us = row.get('SDO_US', 0)
    try:
        sdo_us = float(sdo_us)
    except:
        sdo_us = 0.0

    if not dates or sdo_us <= 0:
        return pd.DataFrame()

    periodicity = str(row.get('TIPO AMORTIZACION', '')).strip().upper()
    credito_id = row.get('ID_CREDITO')

    flow = []
    current_balance = sdo_us
    n_periods = len(dates)

    if periodicity == 'ND' and df_tabla_nd is not None and not df_tabla_nd.empty:
        nd_rows = df_tabla_nd[df_tabla_nd['ID Crédito'].astype(str) == str(credito_id)]

        # We need to map dates to percentages
        # Since tabla_nd has 'Vencimiento' and '% Real', let's map them
        pct_map = {}
        for _, nd_r in nd_rows.iterrows():
            try:
                venc = nd_r['Vencimiento']
                if isinstance(venc, (int, float)):
                    d = pd.to_datetime(venc, unit='D', origin='1899-12-30')
                else:
                    d = pd.to_datetime(venc, errors='coerce')

                if not pd.isna(d):
                    pct_map[d] = float(nd_r.get('% Real', 0))
            except:
                pass

        for d in dates:
            pct = pct_map.get(d, 0.0)
            payment = sdo_us * pct

            # Prevent overpayment if percentages sum to > 1
            if payment > current_balance:
                payment = current_balance

            current_balance -= payment
            # Rounding precision
            if current_balance < 0.001:
                current_balance = 0.0

            flow.append({
                'fecha_operacion': d,
                'pago_amortizacion': payment,
                'saldo_insoluto': current_balance
            })

    else:
        # Standard even distribution
        # Note: If it's a bullet, n_periods will be 1, so payment = sdo_us / 1 = sdo_us. This naturally works.
        payment = sdo_us / n_periods
        for i, d in enumerate(dates):
            if i == n_periods - 1:
                # Last period, pay whatever is left
                payment = current_balance

            current_balance -= payment
            if current_balance < 0.001:
                current_balance = 0.0

            flow.append({
                'fecha_operacion': d,
                'pago_amortizacion': payment,
                'saldo_insoluto': current_balance
            })

    return pd.DataFrame(flow)
