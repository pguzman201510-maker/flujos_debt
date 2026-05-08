import pandas as pd
from modules.calendar_generator import generate_interest_calendar

guias = pd.Series({
    'ID_CREDITO': '1',
    'FECHA INICIAL INTERES': '2026-01-01',
    'FECHA FINAL INTERES': '2027-01-01',
    'PERIODICIDAD PAGO INTERESES': '2'
})

print("Interest Calendar 2:", generate_interest_calendar(guias, "2026-04-30"))

guias_guia = pd.Series({
    'ID_CREDITO': '1',
    'FECHA INICIAL INTERES': '2026-01-01',
    'FECHA FINAL INTERES': '2027-01-01',
    'PERIODICIDAD PAGO INTERESES': 'GUIA',
    'MES PERIODICIDAD': '12'
})

print("Interest Calendar GUIA:", generate_interest_calendar(guias_guia, "2026-04-30"))
