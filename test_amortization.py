import pandas as pd
from modules.amortization_engine import build_amortization_flow

df_nd = pd.DataFrame({
    'ID Crédito': ['ND123', 'ND123'],
    'Vencimiento': [46000, 46500],
    '% Real': [0.4, 0.6]
})

d1 = pd.to_datetime(46000, unit='D', origin='1899-12-30')
d2 = pd.to_datetime(46500, unit='D', origin='1899-12-30')

# Standard
row_std = {'SDO_US': 1000, 'TIPO AMORTIZACION': '1', 'ID_CREDITO': '1'}
dates_std = [pd.to_datetime('2025-01-01'), pd.to_datetime('2026-01-01')]
df_flow_std = build_amortization_flow(row_std, dates_std, df_nd)
print("Standard Flow:\n", df_flow_std)

# ND
row_nd = {'SDO_US': 1000, 'TIPO AMORTIZACION': 'ND', 'ID_CREDITO': 'ND123'}
dates_nd = [d1, d2]
df_flow_nd = build_amortization_flow(row_nd, dates_nd, df_nd)
print("\nND Flow:\n", df_flow_nd)
