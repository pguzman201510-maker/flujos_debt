import pandas as pd
import os
from main import run_projection
from modules.file_reader import read_file
from config.settings import (
    FILE_ORACLE, FILE_INVENTARIO, FILE_GUIAS,
    FILE_TABLA_ND, FILE_TASAS
)

def run_sensibilidad():
    print("=== HERRAMIENTA DE SENSIBILIDAD AVANZADA ===")

    # 1. Select Shocks to Apply
    print("\n¿Qué choques desea aplicar?")
    print("1. Solo Tasa de Cambio")
    print("2. Solo Tasa de Interés")
    print("3. Ambos")
    choice = input("Seleccione (1-3): ").strip()

    shock_tc = 0.0
    shock_int = 0.0
    shock_target = 'AMBAS'

    if choice in ['1', '3']:
        try:
            shock_tc_input = input("Ingrese choque Tasa de Cambio (%): ")
            shock_tc = float(shock_tc_input) if shock_tc_input.strip() else 0.0
        except ValueError: pass

    if choice in ['2', '3']:
        try:
            shock_int_input = input("Ingrese choque Tasa de Interés (%): ")
            shock_int = float(shock_int_input) if shock_int_input.strip() else 0.0

            print("\n¿A qué tasas aplicar el choque de interés?")
            print("1. Solo Tasas Variables")
            print("2. Solo Tasas Fijas")
            print("3. Ambas")
            target_choice = input("Seleccione (1-3): ").strip()
            if target_choice == '1': shock_target = 'VARIABLE'
            elif target_choice == '2': shock_target = 'FIJA'
            else: shock_target = 'AMBAS'
        except ValueError: pass

    print("\nLeyendo archivos de origen...")
    df_oracle = read_file(FILE_ORACLE)
    df_inventario = read_file(FILE_INVENTARIO)
    df_guias = read_file(FILE_GUIAS)
    df_tabla_nd = read_file(FILE_TABLA_ND)
    df_tasas = read_file(FILE_TASAS)

    if df_oracle is None:
        print("Error: No se pudo leer el archivo de Oracle.")
        return

    print("\nProcesando Escenario BASE (Sin choques)...")
    base_flows, _ = run_projection(df_oracle, df_inventario, df_guias, df_tabla_nd, df_tasas, shock_tc=0.0, shock_int=0.0)
    df_base = pd.concat(base_flows, ignore_index=True) if base_flows else pd.DataFrame()

    print("Procesando Escenario SENSIBILIZADO...")
    shock_flows, _ = run_projection(df_oracle, df_inventario, df_guias, df_tabla_nd, df_tasas, shock_tc=shock_tc, shock_int=shock_int, shock_target=shock_target)
    df_shock = pd.concat(shock_flows, ignore_index=True) if shock_flows else pd.DataFrame()

    if df_base.empty or df_shock.empty:
        print("Error: No se generaron flujos para comparar.")
        return

    # SUMMARY CALCULATIONS - INTERESTS (Granular)
    base_int_total = df_base['pago_interes'].sum()
    shock_int_total = df_shock['pago_interes'].sum()

    int_summary_list = [{
        'Concepto': 'Choque Tasa Interés (TOTAL)',
        'Shock %': f"{shock_int}%",
        'Destino': shock_target,
        'Saldo Antes (Int)': base_int_total,
        'Saldo Con Shock (Int)': shock_int_total,
        'Sensibilidad (Dif)': shock_int_total - base_int_total,
        'Sensibilidad % pts': ((shock_int_total / base_int_total) - 1) * 100 if base_int_total != 0 else 0
    }]

    # Group by CLASE_INT
    if 'CLASE_INT' in df_base.columns:
        indices = df_base['CLASE_INT'].unique()
        for idx in indices:
            b_val = df_base[df_base['CLASE_INT'] == idx]['pago_interes'].sum()
            s_val = df_shock[df_shock['CLASE_INT'] == idx]['pago_interes'].sum()
            if b_val > 0 or s_val > 0:
                int_summary_list.append({
                    'Concepto': f"  > {idx}",
                    'Shock %': "", 'Destino': "",
                    'Saldo Antes (Int)': b_val,
                    'Saldo Con Shock (Int)': s_val,
                    'Sensibilidad (Dif)': s_val - b_val,
                    'Sensibilidad % pts': ((s_val / b_val) - 1) * 100 if b_val != 0 else 0
                })
    resumen_interes = pd.DataFrame(int_summary_list)

    # SUMMARY CALCULATIONS - EXCHANGE RATE (Granular)
    base_usd_total = df_base['pago_amortizacion'].sum()
    shock_usd_total = df_shock['pago_amortizacion'].sum()

    tc_summary_list = [{
        'Concepto': 'Choque Tasa Cambio (TOTAL)',
        'Shock %': f"{shock_tc}%",
        'Tasa Cambio Prom. Base': "",
        'Tasa Cambio Prom. Shock': "",
        'Saldo Antes (USD Total)': base_usd_total,
        'Saldo Con Shock (USD Total)': shock_usd_total,
        'Sensibilidad (Dif USD)': shock_usd_total - base_usd_total,
        'Sensibilidad % pts': ((shock_usd_total / base_usd_total) - 1) * 100 if base_usd_total != 0 else 0
    }]

    # Group by Currency (MDA_TR)
    if 'MDA_TR' in df_base.columns:
        mda_list = df_base['MDA_TR'].unique()
        for m in mda_list:
            b_usd = df_base[df_base['MDA_TR'] == m]['pago_amortizacion'].sum()
            s_usd = df_shock[df_shock['MDA_TR'] == m]['pago_amortizacion'].sum()

            # Calculate implicit exchange rate for this currency
            # We look at the first row of this currency in both DFs
            try:
                # In our model, conv_factor = saldo_real / sdo_us
                # base_tc = conv_factor
                b_row = df_base[df_base['MDA_TR'] == m].iloc[0]
                s_row = df_shock[df_shock['MDA_TR'] == m].iloc[0]

                # Check if it has real currency columns
                if 'amort_mda_real' in b_row and b_row['pago_amortizacion'] > 0:
                    tc_base = b_row['amort_mda_real'] / b_row['pago_amortizacion']
                    tc_shock = s_row['amort_mda_real'] / s_row['pago_amortizacion']
                else:
                    tc_base = 1.0
                    tc_shock = 1.0
            except:
                tc_base = 0.0
                tc_shock = 0.0

            if b_usd > 0 or s_usd > 0:
                tc_summary_list.append({
                    'Concepto': f"  > {m}",
                    'Shock %': "",
                    'Tasa Cambio Prom. Base': tc_base,
                    'Tasa Cambio Prom. Shock': tc_shock,
                    'Saldo Antes (USD Total)': b_usd,
                    'Saldo Con Shock (USD Total)': s_usd,
                    'Sensibilidad (Dif USD)': s_usd - b_usd,
                    'Sensibilidad % pts': ((s_usd / b_usd) - 1) * 100 if b_usd != 0 else 0
                })

    resumen_tc = pd.DataFrame(tc_summary_list)

    # EXPORT
    output_file = "flujo_sensibilidad.xlsx"
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_shock.to_excel(writer, sheet_name='Flujo_Sensibilizado', index=False)

            # Write Resumen Sheet
            resumen_interes.to_excel(writer, sheet_name='Resumen_Sensibilidad', startrow=1, index=False)

            # Calculate dynamic start for TC summary
            tc_start = len(resumen_interes) + 4
            resumen_tc.to_excel(writer, sheet_name='Resumen_Sensibilidad', startrow=tc_start, index=False)

            # Format Resumen sheet slightly
            ws = writer.sheets['Resumen_Sensibilidad']
            ws['A1'] = "RESUMEN DE SENSIBILIDAD - INTERESES"
            ws[f'A{tc_start}'] = "RESUMEN DE SENSIBILIDAD - TASA DE CAMBIO"

        print(f"\nProceso exitoso. Resultados en: {output_file}")
    except Exception as e:
        print(f"Error al exportar Excel: {e}")

if __name__ == '__main__':
    run_sensibilidad()
