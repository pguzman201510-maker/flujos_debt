import pandas as pd
from dateutil.relativedelta import relativedelta
from modules.interest_engine import calculate_interest_flow

df_amort = pd.DataFrame({'fecha_operacion': [pd.to_datetime('2028-12-15')], 'saldo_insoluto': [0.0]})
interest_dates = [pd.to_datetime('2026-06-15'), pd.to_datetime('2026-12-15'), pd.to_datetime('2027-06-15'), pd.to_datetime('2027-12-15'), pd.to_datetime('2028-06-15'), pd.to_datetime('2028-12-15')]

row_oracle = {'CLASE_INT': 'FIJA', 'MARGEN_VALOR': 4.0965, 'SDO_US': 297694990.22}
row_guias = {'FECHA INICIAL INTERES': '2025-12-15', 'PERIODICIDAD PAGO INTERESES': '2', 'METODO CONTEO': '5'}
df_tasas = pd.DataFrame()

def mock_day_count(start, end, method):
    from modules.day_count import compute_day_count
    return compute_day_count(start, end, method)

res = calculate_interest_flow(interest_dates, df_amort, row_oracle, row_guias, df_tasas, mock_day_count)
print(res)
