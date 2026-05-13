import pandas as pd
from modules.file_reader import read_file
df_inv = read_file("proy_inventario_perfil.xls")
df_guias = read_file("proy_consulta_guias.xls")

print("Inventario MARGEN VALOR sample:")
print(df_inv[df_inv['MARGEN VALOR'].notna() & (df_inv['MARGEN VALOR'] != 0) & (df_inv['MARGEN VALOR'] != '0')][['CREDITO', 'MARGEN VALOR']].head(10))

print("\nGuias MARGEN VALOR sample:")
print(df_guias[df_guias['MARGEN VALOR'].notna() & (df_guias['MARGEN VALOR'] != 0) & (df_guias['MARGEN VALOR'] != '0')][['CREDITO', 'MARGEN VALOR']].head(10))
