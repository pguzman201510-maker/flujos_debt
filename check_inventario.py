import pandas as pd

try:
    df = pd.read_csv("proy_inventario_perfil.xls", sep='\t', encoding='latin-1')
    print("INVENTARIO columns:", df.columns.tolist())
except Exception as e:
    print(e)
