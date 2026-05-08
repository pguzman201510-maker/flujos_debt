import pandas as pd

def build_id(df, col_credito='COD_CREDITO', col_tramo='NUM_TRAMO', id_col_name='ID_CREDITO'):
    """
    Builds a standard ID from COD_CREDITO and NUM_TRAMO.
    ID logic: COD_CREDITO + "000" + NUM_TRAMO
    """
    if col_credito not in df.columns or col_tramo not in df.columns:
        return df

    def clean_val(val):
        if pd.isna(val):
            return ""
        s = str(val).strip()
        if s.endswith('.0'):
            s = s[:-2]
        return s

    df_clean = df.copy()
    credito = df_clean[col_credito].apply(clean_val)
    tramo = df_clean[col_tramo].apply(clean_val)

    df_clean[id_col_name] = credito + "000" + tramo

    # We should handle missing or empty parts if needed, but standard logic implies string concat
    df_clean.loc[(credito == "") | (tramo == ""), id_col_name] = pd.NA

    return df_clean
