import logging
import pandas as pd

logger = logging.getLogger(__name__)

def validate_data(df_oracle, df_inventario, df_guias):
    """
    Validates merged or separate datasets and logs warnings for inconsistencies.
    """
    logger.info("Starting data validations...")

    # 1. SDO_US = 0 (Should be filtered, but log it if present before filtering)
    if 'SDO_US' in df_oracle.columns:
        sdo_zero = df_oracle[df_oracle['SDO_US'] == 0]
        if not sdo_zero.empty:
            logger.warning(f"Found {len(sdo_zero)} credits with SDO_US = 0 in Consulta Oracle.")

    # 2. Duplicate credits in Oracle (by ID_CREDITO)
    if 'ID_CREDITO' in df_oracle.columns:
        duplicates = df_oracle[df_oracle.duplicated('ID_CREDITO', keep=False)]
        if not duplicates.empty:
            logger.warning(f"Found {len(duplicates['ID_CREDITO'].unique())} duplicate ID_CREDITOs in Consulta Oracle.")

    # 3. Missing IDs
    if 'ID_CREDITO' in df_oracle.columns:
        missing_ids = df_oracle[df_oracle['ID_CREDITO'].isna()]
        if not missing_ids.empty:
            logger.warning(f"Found {len(missing_ids)} records with missing ID_CREDITO in Consulta Oracle.")

    # 4. ULT_PAGO < PRIM_PAGO
    if 'PRIM_PAGO' in df_oracle.columns and 'ULT_PAGO' in df_oracle.columns:
        # Assuming dates are parsed or string format YYYY-MM-DD
        try:
            prim_pago = pd.to_datetime(df_oracle['PRIM_PAGO'], errors='coerce')
            ult_pago = pd.to_datetime(df_oracle['ULT_PAGO'], errors='coerce')

            invalid_dates = df_oracle[(ult_pago < prim_pago)]
            if not invalid_dates.empty:
                logger.warning(f"Found {len(invalid_dates)} credits where ULT_PAGO < PRIM_PAGO.")

            missing_dates = df_oracle[prim_pago.isna() | ult_pago.isna()]
            if not missing_dates.empty:
                logger.warning(f"Found {len(missing_dates)} credits with missing or empty PRIM_PAGO or ULT_PAGO in Consulta Oracle.")
        except Exception as e:
            logger.error(f"Error parsing dates for validation: {e}")

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
