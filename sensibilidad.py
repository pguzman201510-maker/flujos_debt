import pandas as pd
from main import run_projection
from modules.file_reader import read_file
from modules.exporter import export_flow
from config.settings import (
    FILE_ORACLE, FILE_INVENTARIO, FILE_GUIAS,
    FILE_TABLA_ND, FILE_TASAS
)

def run_sensibilidad():
    print("=== HERRAMIENTA DE SENSIBILIDAD DE FLUJOS ===")
    try:
        shock_tc_input = input("Ingrese el choque a la Tasa de Cambio (en %, ej: 5 para +5%, -2 para -2%): ")
        shock_tc = float(shock_tc_input) if shock_tc_input.strip() else 0.0
    except ValueError:
        print("Valor inválido. Se asumirá 0.0%")
        shock_tc = 0.0

    try:
        shock_int_input = input("Ingrese el choque a la Tasa de Interés (en %, ej: 1.5 para +1.5%, -1 para -1%): ")
        shock_int = float(shock_int_input) if shock_int_input.strip() else 0.0
    except ValueError:
        print("Valor inválido. Se asumirá 0.0%")
        shock_int = 0.0

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
    shock_flows, _ = run_projection(df_oracle, df_inventario, df_guias, df_tabla_nd, df_tasas, shock_tc=shock_tc, shock_int=shock_int)
    df_shock = pd.concat(shock_flows, ignore_index=True) if shock_flows else pd.DataFrame()

    # Sum totals
    base_amort = df_base['pago_amortizacion'].sum() if not df_base.empty and 'pago_amortizacion' in df_base else 0.0
    base_int = df_base['pago_interes'].sum() if not df_base.empty and 'pago_interes' in df_base else 0.0

    shock_amort = df_shock['pago_amortizacion'].sum() if not df_shock.empty and 'pago_amortizacion' in df_shock else 0.0
    shock_int_val = df_shock['pago_interes'].sum() if not df_shock.empty and 'pago_interes' in df_shock else 0.0

    print("\n" + "="*50)
    print("RESULTADOS DE LA SENSIBILIDAD")
    print("="*50)
    print(f"Choque Tasa de Cambio aplicado : {shock_tc}%")
    print(f"Choque Tasa de Interés aplicado: {shock_int}%")
    print("-" * 50)
    print(f"{'Concepto':<20} | {'BASE':<15} | {'SHOCK':<15} | {'DIFERENCIA':<15}")
    print("-" * 50)
    print(f"{'Total Amortización':<20} | {base_amort:15,.2f} | {shock_amort:15,.2f} | {shock_amort - base_amort:15,.2f}")
    print(f"{'Total Intereses':<20} | {base_int:15,.2f} | {shock_int_val:15,.2f} | {shock_int_val - base_int:15,.2f}")
    print("="*50)

    # Export shocked flow
    output_file = "flujo_sensibilidad.xlsx"
    export_flow(shock_flows, output_file)
    print(f"\nFlujo sensibilizado exportado exitosamente a: {output_file}")

if __name__ == '__main__':
    run_sensibilidad()
