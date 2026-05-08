from config.settings import FILE_ORACLE, FILE_INVENTARIO, FILE_GUIAS, FILE_TABLA_ND
from modules.file_reader import read_file

df1 = read_file(FILE_ORACLE)
print(f"Oracle columns: {len(df1.columns) if df1 is not None else 0}")

df2 = read_file(FILE_INVENTARIO)
print(f"Inventario columns: {len(df2.columns) if df2 is not None else 0}")

df3 = read_file(FILE_GUIAS)
print(f"Guias columns: {len(df3.columns) if df3 is not None else 0}")

df4 = read_file(FILE_TABLA_ND)
print(f"Tabla ND columns: {len(df4.columns) if df4 is not None else 0}")
