import pandas as pd
with open("proy_inventario_perfil.xls", "r", encoding="latin-1") as f:
    header = f.readline().strip().split('\t')
    print("Header fields:", len(header))
    data = f.readline().strip().split('\t')
    print("Data fields:", len(data))

    # Let's align
    for h, d in zip(header, data):
        print(f"{h[:20]:20} | {d[:50]}")
