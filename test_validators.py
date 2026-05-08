import pandas as pd
import logging
from modules.validators import validate_data

logging.basicConfig(level=logging.WARNING)

oracle = pd.DataFrame({
    'ID_CREDITO': ['A', 'A', None, 'B', 'C'],
    'SDO_US': [0, 100, 50, 200, 300],
    'PRIM_PAGO': ['2025-01-01', '2025-01-01', '2025-01-01', '2026-01-01', None],
    'ULT_PAGO': ['2024-01-01', '2026-01-01', '2026-01-01', '2026-01-01', '2026-01-01']
})

inventario = pd.DataFrame({
    'TIPO AMORTIZACION': ['1', '3', 'ND', '12', None]
})

guias = pd.DataFrame({
    'TIPO DE TASA': ['FIJA', None, '', 'VARIABLE']
})

validate_data(oracle, inventario, guias)
