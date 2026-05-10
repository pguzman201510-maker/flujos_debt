import pandas as pd
import logging

logger = logging.getLogger(__name__)

def export_flow(flow_list, output_path):
    """
    Consolidates the list of flows and exports to an Excel file.
    Output columns: COD_CREDITO, MDA_TR, PMISTA, fecha_operacion, pago_amortizacion, pago_interes, tasa_aplicada
    """
    if not flow_list:
        logger.warning("No flows to export.")
        return

    df_consolidated = pd.concat(flow_list, ignore_index=True)

    expected_cols = ['COD_CREDITO', 'MDA_TR', 'PMISTA', 'fecha_operacion', 'pago_amortizacion', 'pago_interes', 'tasa_aplicada']

    # Ensure columns exist, fill with missing if they don't
    for col in expected_cols:
        if col not in df_consolidated.columns:
            df_consolidated[col] = pd.NA

    df_final = df_consolidated[expected_cols].copy()

    # Sort
    df_final.sort_values(by=['COD_CREDITO', 'fecha_operacion'], inplace=True)

    try:
        df_final.to_excel(output_path, index=False)
        logger.info(f"Successfully exported flows to {output_path}")
    except Exception as e:
        logger.error(f"Failed to export flows: {e}")
