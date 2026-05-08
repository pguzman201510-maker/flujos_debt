import pandas as pd
from modules.interest_engine import calculate_interest_flow

# Mock the day count
def compute_day_count(start, end, method):
    # Just a mock factor
    return 180, 0.5

df_amort = pd.DataFrame({
    'fecha_operacion': [pd.to_datetime('2026-06-01')],
    'saldo_insoluto': [0.0]
})

interest_dates = [pd.to_datetime('2026-06-01'), pd.to_datetime('2026-12-01')]

row_oracle = {'CLASE_INT': 'ISOR', 'MARGEN_VALOR': 1.0, 'SDO_US': 1000.0}
row_guias = {'FECHA INICIAL INTERES': '2025-12-01', 'METODO CONTEO': '1'}
df_tasas = pd.DataFrame({'Fecha': [pd.to_datetime('2026-06-01'), pd.to_datetime('2026-12-01')], 'ISOR': [4.0, 5.0]})

res = calculate_interest_flow(interest_dates, df_amort, row_oracle, row_guias, df_tasas, compute_day_count)
print(res)
