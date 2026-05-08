import pandas as pd
from modules.file_reader import read_file

df_guias = read_file("proy_consulta_guias.xls")
df_inventario = read_file("proy_inventario_perfil.xls")

print("GUIAS 511100166", df_guias[df_guias["CREDITO"].astype(str) == "511100166"].to_string())
print("INV 511100166", df_inventario[df_inventario["CREDITO"].astype(str) == "511100166"][["CREDITO", "PERIODICIDAD PAGO INTERESES"]].to_string())
