import pandas as pd
from modules.calendar_generator import generate_calendar

cutoff = "2026-04-30"

df_nd = pd.DataFrame({
    'ID Crédito': ['ND123', 'ND123'],
    'Vencimiento': [46000, 46500] # Some excel dates
})

# Test Bullet
row_bullet = {'ID_CREDITO': '1', 'PRIM_PAGO': '2027-01-01', 'ULT_PAGO': '2027-01-01', 'TIPO AMORTIZACION': '1'}
print("Bullet:", generate_calendar(row_bullet, df_nd, cutoff))

# Test Annual
row_ann = {'ID_CREDITO': '2', 'PRIM_PAGO': '2025-01-01', 'ULT_PAGO': '2028-01-01', 'TIPO AMORTIZACION': '1'}
print("Annual:", generate_calendar(row_ann, df_nd, cutoff))

# Test Monthly
row_mon = {'ID_CREDITO': '3', 'PRIM_PAGO': '2026-03-01', 'ULT_PAGO': '2026-06-01', 'TIPO AMORTIZACION': '12'}
print("Monthly:", generate_calendar(row_mon, df_nd, cutoff))

# Test ND
row_nd = {'ID_CREDITO': 'ND123', 'PRIM_PAGO': '2026-01-01', 'ULT_PAGO': '2028-01-01', 'TIPO AMORTIZACION': 'ND'}
print("ND:", generate_calendar(row_nd, df_nd, cutoff))
