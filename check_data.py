import pandas as pd

def read_file(name):
    try:
        return pd.read_csv(name, sep='\t')
    except Exception:
        try:
            return pd.read_excel(name)
        except Exception as e:
            return str(e)

guias = read_file("proy_consulta_guias.xls")
inventario = read_file("proy_inventario_perfil.xls")
tabla_nd = pd.read_excel("tabla_nd.xlsx")
tasas = pd.read_excel("Tasas_forward.xlsx")

print("GUIAS columns:", guias.columns.tolist())
print("GUIAS METODO CONTEO unique:", guias['METODO CONTEO'].unique() if 'METODO CONTEO' in guias else "No METODO CONTEO")

print("INVENTARIO columns:", inventario.columns.tolist())
print("TABLA ND columns:", tabla_nd.columns.tolist())
