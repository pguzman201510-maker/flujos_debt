import os
import logging
import pandas as pd

from config.settings import (
    FILE_ORACLE, FILE_INVENTARIO, FILE_GUIAS,
    FILE_TABLA_ND, FILE_TASAS, FILE_OUTPUT, CUTOFF_DATE, FIXED_RATE_CODES
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

def run_projection(df_oracle, df_inventario, df_guias, df_tabla_nd, df_tasas, shock_tc=0.0, shock_int=0.0):
    """
    Runs the entire cash flow generation logic on the provided dataframes.
    shock_tc: Percentage shock to the implicit exchange rate (e.g. 5.0 for +5%).
    shock_int: Percentage shock to the interest rate (e.g. 1.0 for +1% flat).
    Returns (all_flows, missing_nd_credits)
    """
    # Clone to avoid mutating original source data directly
    df_oracle = df_oracle.copy()

    # Filter SDO_US != 0
    if 'SDO_US' in df_oracle.columns:
        df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
        df_oracle = df_oracle[df_oracle['SDO_US'] > 0]

    # 2. Build IDs
    df_oracle = build_id(df_oracle)
    if df_inventario is not None:
        df_inventario = build_id(df_inventario, col_credito='CREDITO', col_tramo='TRAMO')
    if df_guias is not None:
        df_guias = build_id(df_guias, col_credito='CREDITO', col_tramo='TRAMO')

    # Prepare merged lookups
    inventario_lookup = df_inventario.set_index('ID_CREDITO') if df_inventario is not None and 'ID_CREDITO' in df_inventario.columns else pd.DataFrame()
    guias_lookup = df_guias.set_index('ID_CREDITO') if df_guias is not None and 'ID_CREDITO' in df_guias.columns else pd.DataFrame()

    all_flows = []
    missing_nd_credits = []

    # Process each credit
    for _, row in df_oracle.iterrows():
        cred_id = row.get('ID_CREDITO')
        if pd.isna(cred_id):
            continue

        inv_row = inventario_lookup.loc[cred_id] if cred_id in inventario_lookup.index else pd.Series()
        guias_row = guias_lookup.loc[cred_id] if cred_id in guias_lookup.index else pd.Series()

        # If multiple matches, just take the first one
        if isinstance(inv_row, pd.DataFrame):
            inv_row = inv_row.iloc[0]

        if isinstance(guias_row, pd.DataFrame):
            # Pick the active guide (FECHA FINAL INTERES >= CUTOFF_DATE)
            active_guias = []
            for _, g_row in guias_row.iterrows():
                end_date = pd.to_datetime(g_row.get('FECHA FINAL INTERES'), errors='coerce')
                if not pd.isna(end_date) and end_date >= pd.to_datetime(CUTOFF_DATE):
                    active_guias.append(g_row)
            if active_guias:
                guias_row = active_guias[0]
            else:
                guias_row = guias_row.iloc[-1]

        # Combine into a single dict-like structure for easy access
        combined_row = {**row.to_dict(), **inv_row.to_dict(), **guias_row.to_dict()}
        # For guias, we just pass the row to interest engine later

        # --- SHOCK TC LOGIC ---
        if shock_tc != 0.0:
            mda_tr = str(combined_row.get('MDA_TR', '')).strip().upper()
            try:
                sdo_us = float(combined_row.get('SDO_US', 0.0))
                saldo_real = float(combined_row.get('SALDO_REAL', 0.0))
                if saldo_real == 0:
                    saldo_real = float(combined_row.get('SALDO_PAGO', 0.0))

                if sdo_us > 0 and saldo_real > 0:
                    # Calculate implied exchange rate
                    if mda_tr == 'COP':
                        implicit_rate = saldo_real / sdo_us
                    else:
                        implicit_rate = sdo_us / saldo_real

                    # Apply shock to the rate
                    shocked_rate = implicit_rate * (1 + shock_tc / 100.0)

                    # Recalculate SDO_US
                    if mda_tr == 'COP':
                        new_sdo_us = saldo_real / shocked_rate
                    else:
                        new_sdo_us = saldo_real * shocked_rate

                    # Inject back
                    combined_row['SDO_US'] = new_sdo_us
                    row['SDO_US'] = new_sdo_us
            except Exception as e:
                logger.debug(f"Failed to apply TC shock to {cred_id}: {e}")
        # -----------------------

        # We might need to map empty dates from Guias as per requirements
        if pd.isna(combined_row.get('PRIM_PAGO')):
            # If dates missing, try to get from Guias or inventario (FECHA PRIMER PAGO)
            if 'FECHA PRIMER PAGO' in combined_row and not pd.isna(combined_row['FECHA PRIMER PAGO']):
                combined_row['PRIM_PAGO'] = combined_row['FECHA PRIMER PAGO']
        if pd.isna(combined_row.get('ULT_PAGO')):
            if 'FECHA VENCIMIENTO' in combined_row and not pd.isna(combined_row['FECHA VENCIMIENTO']):
                combined_row['ULT_PAGO'] = combined_row['FECHA VENCIMIENTO']

        # Track missing ND credits
        periodicity = str(combined_row.get('TIPO AMORTIZACION', '')).strip().upper()
        if periodicity == 'ND':
            if df_tabla_nd is None or df_tabla_nd.empty or not (df_tabla_nd['ID Crédito'].astype(str) == str(cred_id)).any():
                if cred_id not in missing_nd_credits:
                    missing_nd_credits.append(cred_id)

        # 5. Generate calendars
        dates = generate_calendar(combined_row, df_tabla_nd, CUTOFF_DATE)
        from modules.calendar_generator import generate_interest_calendar
        interest_dates = generate_interest_calendar(combined_row, CUTOFF_DATE)

        # 6. Build Amortization
        df_amort_flow = build_amortization_flow(combined_row, dates, df_tabla_nd)

        # 7. Build Interest
        df_interest_flow = calculate_interest_flow(
            interest_dates=interest_dates,
            df_amortization_flow=df_amort_flow,
            row_oracle=row,
            row_inv=inv_row,
            row_guias=guias_row,
            df_tasas=df_tasas,
            compute_day_count=compute_day_count,
            shock_int=shock_int
        )

        # 8. Combine flows
        if not df_amort_flow.empty and not df_interest_flow.empty:
            df_combined = pd.merge(df_amort_flow, df_interest_flow, on='fecha_operacion', how='outer')
        elif not df_amort_flow.empty:
            df_combined = df_amort_flow.copy()
            df_combined['pago_interes'] = 0.0
            df_combined['tasa_aplicada'] = pd.NA
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
            if 'tasa_aplicada' not in df_combined.columns:
                df_combined['tasa_aplicada'] = pd.NA

            # Attach basic info
            df_combined['ID_CREDITO'] = row.get('ID_CREDITO')
            df_combined['COD_CREDITO'] = row.get('COD_CREDITO')
            df_combined['MDA_TR'] = row.get('MDA_TR')
            df_combined['PMISTA'] = row.get('PMISTA')

            clase_int = str(row.get('CLASE_INT', '')).strip()
            df_combined['CLASE_INT'] = clase_int
            df_combined['tipo_tasa'] = 'FIJA' if clase_int in FIXED_RATE_CODES else 'VARIABLE'
            df_combined['metodo_conteo'] = guias_row.get('METODO CONTEO')

            # --- CONVERT TO LOCAL CURRENCY LOGIC ---
            try:
                sdo_us_orig = float(row.get('SDO_US', 0.0))
                saldo_real_orig = float(row.get('SALDO_REAL', 0.0))
                if saldo_real_orig == 0:
                    saldo_real_orig = float(row.get('SALDO_PAGO', 0.0))

                if sdo_us_orig > 0 and saldo_real_orig > 0:
                    conv_factor = saldo_real_orig / sdo_us_orig
                else:
                    conv_factor = 1.0
            except:
                conv_factor = 1.0

            df_combined['amort_mda_real'] = df_combined['pago_amortizacion'] * conv_factor
            df_combined['intereses_mda_real'] = df_combined['pago_interes'] * conv_factor

            all_flows.append(df_combined)

    return all_flows, missing_nd_credits

def main():
    logger.info("Starting Flow Generator...")

    # Read files
    df_oracle = read_file(FILE_ORACLE)
    df_inventario = read_file(FILE_INVENTARIO)
    df_guias = read_file(FILE_GUIAS)
    df_tabla_nd = read_file(FILE_TABLA_ND)
    df_tasas = read_file(FILE_TASAS)

    if df_oracle is None:
        logger.error("Oracle file could not be read. Exiting.")
        return

    # Validations run once on original data
    validate_data(df_oracle, df_inventario, df_guias)

    # Run core projection logic
    all_flows, missing_nd_credits = run_projection(
        df_oracle, df_inventario, df_guias, df_tabla_nd, df_tasas
    )

    # Export
    export_flow(all_flows, FILE_OUTPUT)

    # Print missing ND Summary
    if missing_nd_credits:
        print("\n" + "="*50)
        print("RESUMEN DE CRÉDITOS 'ND' NO ENCONTRADOS EN TABLA ND")
        print("="*50)
        print("Los siguientes créditos tienen tipo de amortización 'ND',")
        print("pero no se encontró su flujo de pago en 'tabla_nd.xlsx':\n")
        for c in missing_nd_credits:
            print(f" - {c}")
        print("="*50 + "\n")

    logger.info("Processing complete.")

if __name__ == "__main__":
    main()
