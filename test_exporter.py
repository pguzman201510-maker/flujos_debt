import pandas as pd
from modules.exporter import export_flow

flows = [
    pd.DataFrame({
        'COD_CREDITO': ['C1', 'C1'],
        'MDA_TR': ['USD', 'USD'],
        'PMISTA': ['BID', 'BID'],
        'fecha_operacion': [pd.to_datetime('2026-01-01'), pd.to_datetime('2026-06-01')],
        'pago_amortizacion': [100.0, 100.0],
        'pago_interes': [5.0, 4.0]
    })
]

export_flow(flows, 'test_out.xlsx')
