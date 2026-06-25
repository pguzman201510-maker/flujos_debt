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

    # SUMMARY CALCULATIONS
    base_int_total = df_base['pago_interes'].sum()
    shock_int_total = df_shock['pago_interes'].sum()

    # For USD balance, we use SDO_US at the start (Oracle filter already handles > 0)
    # Actually, user wants "saldo en dolares" summary for TC shock.
    # Since TC shock changes SDO_US, we compare total amortizations in USD equivalent.
    base_usd_total = df_base['pago_amortizacion'].sum() # This is in SDO_US (USD equivalent)
    shock_usd_total = df_shock['pago_amortizacion'].sum() # This is the NEW SDO_US after TC shock

    resumen_interes = pd.DataFrame([{
        'Concepto': 'Choque Tasa Interés',
        'Shock %': f"{shock_int}%",
        'Destino': shock_target,
        'Saldo Antes (Intereses Total)': base_int_total,
        'Saldo Con Shock (Intereses Total)': shock_int_total,
        'Sensibilidad (Diferencia)': shock_int_total - base_int_total,
        'Sensibilidad % pts': ((shock_int_total / base_int_total) - 1) * 100 if base_int_total != 0 else 0
    }])

    resumen_tc = pd.DataFrame([{
        'Concepto': 'Choque Tasa Cambio',
        'Shock %': f"{shock_tc}%",
        'Saldo Antes (USD Total)': base_usd_total,
        'Saldo Con Shock (USD Total)': shock_usd_total,
        'Sensibilidad (Diferencia USD)': shock_usd_total - base_usd_total,
        'Sensibilidad % pts': ((shock_usd_total / base_usd_total) - 1) * 100 if base_usd_total != 0 else 0
    }])

    # EXPORT
    output_file = "flujo_sensibilidad.xlsx"
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_shock.to_excel(writer, sheet_name='Flujo_Sensibilizado', index=False)

            # Write Resumen Sheet
            resumen_interes.to_excel(writer, sheet_name='Resumen_Sensibilidad', startrow=1, index=False)
            resumen_tc.to_excel(writer, sheet_name='Resumen_Sensibilidad', startrow=6, index=False)

            # Format Resumen sheet slightly
            ws = writer.sheets['Resumen_Sensibilidad']
            ws['A1'] = "RESUMEN DE SENSIBILIDAD - INTERESES"
            ws['A6'] = "RESUMEN DE SENSIBILIDAD - TASA DE CAMBIO"

        print(f"\nProceso exitoso. Resultados en: {output_file}")
    except Exception as e:
        print(f"Error al exportar Excel: {e}")

if __name__ == '__main__':
    run_sensibilidad()
