import logging
import pandas as pd

logger = logging.getLogger(__name__)

def validate_data(df_oracle, df_inventario, df_guias):
    """
    Validates merged or separate datasets and logs warnings for inconsistencies.
    Returns a list of initial error dicts.
    """
    logger.info("Starting data validations...")
    initial_errors = []

    # 1. SDO_US <= 0
    if 'SDO_US' in df_oracle.columns:
        sdo_zero = df_oracle[pd.to_numeric(df_oracle['SDO_US'], errors='coerce') <= 0]
        for _, r in sdo_zero.iterrows():
            initial_errors.append({
                'ID_CREDITO': f"{r.get('COD_CREDITO')}T{r.get('NUM_TRAMO')}",
                'ERROR': 'SALDO_CERO_O_NEGATIVO',
                'DETALLE': f"Saldo reportado: {r.get('SDO_US')}"
            })

    # 2. Oracle missing in Inventory
    if df_inventario is not None and 'COD_CREDITO' in df_oracle.columns and 'CREDITO' in df_inventario.columns:
        oracle_ids = set(df_oracle['COD_CREDITO'].astype(str).str.strip())
        inv_ids = set(df_inventario['CREDITO'].astype(str).str.strip())
        missing_in_inv = oracle_ids - inv_ids
        for mid in missing_in_inv:
            initial_errors.append({
                'ID_CREDITO': mid,
                'ERROR': 'FALTA_EN_INVENTARIO',
                'DETALLE': "Crédito presente en Oracle pero no en el archivo de Inventario Perfil"
            })

    # 3. Missing IDs
    if 'ID_CREDITO' in df_oracle.columns:
        missing_ids = df_oracle[df_oracle['ID_CREDITO'].isna()]
        if not missing_ids.empty:
            logger.warning(f"Found {len(missing_ids)} records with missing ID_CREDITO in Consulta Oracle.")

    # 4. Far-future maturities
    if 'ULT_PAGO' in df_oracle.columns:
        try:
            ult_pago = pd.to_datetime(df_oracle['ULT_PAGO'], errors='coerce')
            max_date = pd.Timestamp.now() + pd.DateOffset(years=60)
            too_far = df_oracle[ult_pago > max_date]
            for _, r in too_far.iterrows():
                initial_errors.append({
                    'ID_CREDITO': f"{r.get('COD_CREDITO')}T{r.get('NUM_TRAMO')}",
                    'ERROR': 'VENCIMIENTO_MUY_LEJANO',
                    'DETALLE': f"Fecha: {r.get('ULT_PAGO')} (Posible error de digitación)"
                })
        except: pass

    # 5. Invalid periodicities in Inventario
    if 'TIPO AMORTIZACION' in df_inventario.columns:
        valid_pers = ['1', '2', '12', 'ND', 1, 2, 12]
        invalid_pers = df_inventario[~df_inventario['TIPO AMORTIZACION'].isin(valid_pers) & df_inventario['TIPO AMORTIZACION'].notna()]
        if not invalid_pers.empty:
            logger.warning(f"Found {len(invalid_pers)} records with invalid 'TIPO AMORTIZACION' in Inventario.")

    # 6. Missing rates in Guias
    if 'TIPO DE TASA' in df_guias.columns:
        missing_rates = df_guias[df_guias['TIPO DE TASA'].isna() | (df_guias['TIPO DE TASA'].astype(str).str.strip() == '')]
        if not missing_rates.empty:
            logger.warning(f"Found {len(missing_rates)} records with missing 'TIPO DE TASA' in Guias.")

    logger.info("Validations completed.")
    return initial_errors
