import pandas as pd
from modules.file_reader import read_file
df_oracle = read_file("Consulta oracle 30-04-2026.xls")
df_inventario = read_file("proy_inventario_perfil.xls")
df_guias = read_file("proy_consulta_guias.xls")

print("Oracle cols:", list(df_oracle.columns))
print("Inventario cols:", list(df_inventario.columns))
print("Guias cols:", list(df_guias.columns))
