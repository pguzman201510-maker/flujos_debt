import pandas as pd
from modules.id_builder import build_id

df = pd.DataFrame({
    'COD_CREDITO': [541100131, ' 543100035 ', 541100129.0, None],
    'NUM_TRAMO': [2, ' 2.0 ', 2, 1]
})

df_res = build_id(df)
print(df_res[['COD_CREDITO', 'NUM_TRAMO', 'ID_CREDITO']])
