import pandas as pd
from modules.forward_rates import get_forward_rate

df_tasas = pd.DataFrame({
    'Fecha': pd.to_datetime(['2025-01-01', '2025-06-01', '2026-01-01']),
    'ISOR': [4.0, 4.5, 5.0],
    'LUS3': [3.0, 3.5, 4.0]
})

print("Rate ISOR 2025-05-15:", get_forward_rate(df_tasas, 'ISOR', '2025-05-15')) # should be 4.5
print("Rate LUS3 2026-02-01:", get_forward_rate(df_tasas, 'LUS3', '2026-02-01')) # should be 4.0
print("Rate UNKNOWN 2025-01-01:", get_forward_rate(df_tasas, 'UNK', '2025-01-01')) # should be 0.0
