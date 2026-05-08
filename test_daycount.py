from modules.day_count import compute_day_count
import pandas as pd

d1 = pd.to_datetime('2025-01-31')
d2 = pd.to_datetime('2025-02-28')

print("Actual/360:", compute_day_count(d1, d2, '0'))
print("Actual/365 Fixed:", compute_day_count(d1, d2, '1'))
print("30E/360:", compute_day_count(d1, d2, '4'))
