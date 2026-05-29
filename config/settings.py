import os

# Project root path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths
FILE_ORACLE = os.path.join(BASE_DIR, "Consulta oracle 30-04-2026.xls")
FILE_INVENTARIO = os.path.join(BASE_DIR, "proy_inventario_perfil.xls")
FILE_GUIAS = os.path.join(BASE_DIR, "proy_consulta_guias.xls")
FILE_TABLA_ND = os.path.join(BASE_DIR, "tabla_nd.xlsx")
FILE_TASAS = os.path.join(BASE_DIR, "Tasas_forward.xlsx")
FILE_OUTPUT = os.path.join(BASE_DIR, "flujo_proyectado.xlsx")

# Report cutoff date
CUTOFF_DATE = "2026-04-30" # From file name

# Fixed rate indicators
FIXED_RATE_CODES = ["FUFI", "FIJA", "SINI", "FI19"]

# Dynamic Spreads
MBID_RATE = 0.0080 # 0.80% changes quarterly
