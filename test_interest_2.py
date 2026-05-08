import pandas as pd
from modules.interest_engine import calculate_interest_flow

def mock_day_count(start, end, method):
    # Returns half year
    return 180, 0.5

df_amort = pd.DataFrame()
interest_dates = [pd.to_datetime('2026-06-01')]
row_oracle = {'CLASE_INT': 'ISOR', 'MARGEN_VALOR': 1.0, 'SDO_US': 1000.0}
# Start date way in the past (2020)
row_guias = {'FECHA INICIAL INTERES': '2020-06-01', 'PERIODICIDAD PAGO INTERESES': '2'}
df_tasas = pd.DataFrame({'Fecha': [pd.to_datetime('2026-06-01')], 'ISOR': [4.0]})

res = calculate_interest_flow(interest_dates, df_amort, row_oracle, row_guias, df_tasas, mock_day_count)
# It should only accrue for ~6 months, not 6 years. The factor is 0.5 (from our mock).
# So interest should be 1000 * 5% * 0.5 = 25
print(res)
