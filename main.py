import os
import logging
import pandas as pd

from config.settings import (
    FILE_ORACLE, FILE_INVENTARIO, FILE_GUIAS,
    FILE_TABLA_ND, FILE_TASAS, FILE_OUTPUT, CUTOFF_DATE
)
from modules.file_reader import read_file
from modules.id_builder import build_id
from modules.validators import validate_data
from modules.calendar_generator import generate_calendar
from modules.amortization_engine import build_amortization_flow
from modules.interest_engine import calculate_interest_flow
from modules.day_count import compute_day_count
from modules.exporter import export_flow

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Flow Generator...")

    # 1. Read files
    df_oracle = read_file(FILE_ORACLE)
    df_inventario = read_file(FILE_INVENTARIO)
    df_guias = read_file(FILE_GUIAS)
    df_tabla_nd = read_file(FILE_TABLA_ND)
    df_tasas = read_file(FILE_TASAS)

    if df_oracle is None:
        logger.error("Oracle file could not be read. Exiting.")
        return

    # Filter SDO_US != 0
    if 'SDO_US' in df_oracle.columns:
        df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
        df_oracle = df_oracle[df_oracle['SDO_US'] > 0]
        logger.info(f"Filtered to {len(df_oracle)} active credits.")

    # 2. Build IDs
    df_oracle = build_id(df_oracle)
    if df_inventario is not None:
        df_inventario = build_id(df_inventario, col_credito='CREDITO', col_tramo='TRAMO')
    if df_guias is not None:
        df_guias = build_id(df_guias, col_credito='CREDITO', col_tramo='TRAMO')

    # 3. Validations
    validate_data(df_oracle, df_inventario, df_guias)

    # Prepare merged lookups
    inventario_lookup = df_inventario.set_index('ID_CREDITO') if df_inventario is not None and 'ID_CREDITO' in df_inventario.columns else pd.DataFrame()
    guias_lookup = df_guias.set_index('ID_CREDITO') if df_guias is not None and 'ID_CREDITO' in df_guias.columns else pd.DataFrame()

    all_flows = []

    # 4. Process each credit
    for _, row in df_oracle.iterrows():
        cred_id = row.get('ID_CREDITO')
        if pd.isna(cred_id):
            continue

        inv_row = inventario_lookup.loc[cred_id] if cred_id in inventario_lookup.index else pd.Series()
        guias_row = guias_lookup.loc[cred_id] if cred_id in guias_lookup.index else pd.Series()

        # If multiple matches, just take the first one
        if isinstance(inv_row, pd.DataFrame): inv_row = inv_row.iloc[0]
        if isinstance(guias_row, pd.DataFrame): guias_row = guias_row.iloc[0]

        # Combine into a single dict-like structure for easy access
        combined_row = {**row.to_dict(), **inv_row.to_dict(), **guias_row.to_dict()}
        # For guias, we just pass the row to interest engine later

        # We might need to map empty dates from Guias as per requirements
        if pd.isna(combined_row.get('PRIM_PAGO')):
            # If dates missing, try to get from Guias or inventario (FECHA PRIMER PAGO)
            if 'FECHA PRIMER PAGO' in combined_row and not pd.isna(combined_row['FECHA PRIMER PAGO']):
                combined_row['PRIM_PAGO'] = combined_row['FECHA PRIMER PAGO']
        if pd.isna(combined_row.get('ULT_PAGO')):
            if 'FECHA VENCIMIENTO' in combined_row and not pd.isna(combined_row['FECHA VENCIMIENTO']):
                combined_row['ULT_PAGO'] = combined_row['FECHA VENCIMIENTO']

        # 5. Generate calendars
        dates = generate_calendar(combined_row, df_tabla_nd, CUTOFF_DATE)
        from modules.calendar_generator import generate_interest_calendar
        interest_dates = generate_interest_calendar(guias_row, CUTOFF_DATE)

        # 6. Build Amortization
        df_amort_flow = build_amortization_flow(combined_row, dates, df_tabla_nd)

        # 7. Build Interest
        df_interest_flow = calculate_interest_flow(
            interest_dates=interest_dates,
            df_amortization_flow=df_amort_flow,
            row_oracle=row,
            row_guias=guias_row,
            df_tasas=df_tasas,
            compute_day_count=compute_day_count
        )

        # 8. Combine flows
        if not df_amort_flow.empty and not df_interest_flow.empty:
            df_combined = pd.merge(df_amort_flow, df_interest_flow, on='fecha_operacion', how='outer')
        elif not df_amort_flow.empty:
            df_combined = df_amort_flow.copy()
            df_combined['pago_interes'] = 0.0
        elif not df_interest_flow.empty:
            df_combined = df_interest_flow.copy()
            df_combined['pago_amortizacion'] = 0.0
            df_combined['saldo_insoluto'] = pd.NA
        else:
            df_combined = pd.DataFrame()

        if not df_combined.empty:
            # Fill NAs
            if 'pago_amortizacion' in df_combined.columns:
                df_combined['pago_amortizacion'] = df_combined['pago_amortizacion'].fillna(0.0)
            if 'pago_interes' in df_combined.columns:
                df_combined['pago_interes'] = df_combined['pago_interes'].fillna(0.0)

            # Attach basic info
            df_combined['COD_CREDITO'] = row.get('COD_CREDITO')
            df_combined['MDA_TR'] = row.get('MDA_TR')
            df_combined['PMISTA'] = row.get('PMISTA')

            all_flows.append(df_combined)

    # 9. Export
    export_flow(all_flows, FILE_OUTPUT)
    logger.info("Processing complete.")

if __name__ == "__main__":
    main()
