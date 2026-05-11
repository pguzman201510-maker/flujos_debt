from modules.day_count import compute_day_count
import pandas as pd

d1 = pd.to_datetime('2025-01-31')
d2 = pd.to_datetime('2025-02-28')
d3 = pd.to_datetime('2025-03-31')

# 30/360 US
print("0: 30/360 (Jan 31 to Feb 28):", compute_day_count(d1, d2, 0))
print("0: 30/360 (Jan 31 to Mar 31):", compute_day_count(d1, d3, '0'))

# Actual/360
print("2: Actual/360 (Jan 31 to Feb 28):", compute_day_count(d1, d2, 2))

# 30E/360
print("5: 30E/360 (Jan 31 to Mar 31):", compute_day_count(d1, d3, 5))
