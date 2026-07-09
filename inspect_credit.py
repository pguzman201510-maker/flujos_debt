import os
import pandas as pd
import logging
from config.settings import FILE_ORACLE, FILE_INVENTARIO, FILE_GUIAS, FILE_TABLA_ND
from modules.file_reader import read_file
from modules.id_builder import build_id

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def normalize_id(val):
    if pd.isna(val): return ""
    try:
        f = float(val)
        return str(int(f))
    except:
        return str(val).strip()

def inspect_credit(target_id):
    logger.info(f"\n{'='*60}")
    logger.info(f"INSPECCIÓN DE CRÉDITO: {target_id}")
    logger.info(f"{'='*60}\n")

    # Load Data
    df_oracle = build_id(read_file(FILE_ORACLE))
    df_inv = build_id(read_file(FILE_INVENTARIO), col_credito='CREDITO', col_tramo='TRAMO')
    df_guias = build_id(read_file(FILE_GUIAS), col_credito='CREDITO', col_tramo='TRAMO')
    df_nd = read_file(FILE_TABLA_ND)

    target_norm = normalize_id(target_id)
    base_code = target_norm[:9] if len(target_norm) >= 9 else target_norm

    # 1. ORACLE
    logger.info(f"--- [ARCHIVO] Oracle ---")
    match_ora = df_oracle[df_oracle['ID_CREDITO'].astype(str).str.contains(target_norm, na=False)]
    if match_ora.empty:
        # Try numeric
        try:
            nums = pd.to_numeric(df_oracle['ID_CREDITO'], errors='coerce')
            match_ora = df_oracle[ (nums - float(target_norm)).abs() < 1e-3 ]
        except: pass

    if not match_ora.empty:
        row = match_ora.iloc[0]
        cols = ['COD_CREDITO', 'NUM_TRAMO', 'MDA_TR', 'CLASE_INT', 'MARGEN_VALOR', 'SDO_US', 'SALDO_REAL', 'PRIM_PAGO', 'ULT_PAGO']
        for c in cols:
            val = row.get(c)
            explanation = ""
            if c == 'CLASE_INT': explanation = "(Se ignora si existe en Guías)"
            if c == 'SDO_US': explanation = "(Saldo base para la proyección en USD)"
            if c == 'MDA_TR': explanation = "(Moneda de desembolso)"
            logger.info(f"  Col: {c:15} | Valor: {val:15} {explanation}")
    else:
        logger.info("  (!) No se encontró el crédito en el archivo de Consulta Oracle.")

    # 2. INVENTARIO
    logger.info(f"\n--- [ARCHIVO] Inventario Perfil ---")
    match_inv = df_inv[df_inv['ID_CREDITO'].astype(str).str.contains(target_norm, na=False)]
    if match_inv.empty:
        try:
            nums = pd.to_numeric(df_inv['ID_CREDITO'], errors='coerce')
            match_inv = df_inv[ (nums - float(target_norm)).abs() < 1e-3 ]
        except: pass

    if not match_inv.empty:
        row = match_inv.iloc[0]
        cols = ['FECHA PRIMER PAGO', 'FECHA VENCIMIENTO', 'TIPO AMORTIZACION', 'MARGEN VALOR', 'PERIODICIDAD PAGO INTERESES']
        for c in cols:
            val = row.get(c)
            logger.info(f"  Col: {c:25} | Valor: {val}")
            if c == 'FECHA PRIMER PAGO': logger.info("      [Uso] Se usa como ANCLA principal para el ciclo de pagos.")
            if c == 'TIPO AMORTIZACION' and pd.isna(val): logger.info("      [Uso] Al estar vacío, el sistema busca en Tabla ND.")
    else:
        logger.info("  (!) No se encontró el crédito en el archivo de Inventario Perfil.")

    # 3. GUIAS
    logger.info(f"\n--- [ARCHIVO] Consulta Guías ---")
    match_guias = df_guias[df_guias['ID_CREDITO'].astype(str).str.contains(target_norm, na=False)]
    if match_guias.empty:
        try:
            nums = pd.to_numeric(df_guias['ID_CREDITO'], errors='coerce')
            match_guias = df_guias[ (nums - float(target_norm)).abs() < 1e-3 ]
        except: pass

    if not match_guias.empty:
        logger.info(f"  Encontradas {len(match_guias)} guías vigentes/históricas:")
        for i, (_, r) in enumerate(match_guias.iterrows()):
            logger.info(f"  > Guía {i+1} (Días {r.get('FECHA INICIAL INTERES')} a {r.get('FECHA FINAL INTERES')}):")
            logger.info(f"    Col: TASA INTERES     | Valor: {r.get('TASA INTERES')} (Clase proyectada)")
            logger.info(f"    Col: MARGEN VALOR     | Valor: {r.get('MARGEN VALOR')}")
            logger.info(f"    Col: MES PERIODICIDAD | Valor: {r.get('MES PERIODICIDAD')}")
            logger.info(f"    Col: METODO CONTEO    | Valor: {r.get('METODO CONTEO')}")
    else:
        logger.info("  (!) No se encontraron guías para este crédito.")

    # 4. TABLA ND
    logger.info(f"\n--- [ARCHIVO] Tabla ND ---")
    found_nd = False
    if df_nd is not None:
        match_nd = df_nd[df_nd['ID Crédito'].astype(str).str.contains(target_norm, na=False)]
        if match_nd.empty:
            try:
                nums = pd.to_numeric(df_nd['ID Crédito'], errors='coerce')
                match_nd = df_nd[ (nums - float(target_norm)).abs() < 1e-3 ]
            except: pass

        if not match_nd.empty:
            logger.info(f"  Encontradas {len(match_nd)} filas para el TRAMO específico.")
            found_nd = True
        else:
            # Try base code
            match_nd_base = df_nd[df_nd.iloc[:, 0].astype(str).str.contains(base_code, na=False)]
            if not match_nd_base.empty:
                logger.info(f"  (!) Tramo específico no está en ND, pero el CÓDIGO base {base_code} tiene {len(match_nd_base)} filas.")
                match_nd = match_nd_base
                found_nd = True

        if found_nd:
            logger.info(f"  Primeras 3 distribuciones encontradas:")
            for _, r in match_nd.head(3).iterrows():
                logger.info(f"    Fecha: {r.get('Vencimiento')} | %: {r.get('% Real')}")
        else:
            logger.info("  (!) El crédito no tiene distribución irregular (ND) en el archivo.")

    logger.info(f"\n{'='*60}")
    logger.info("FIN DE LA INSPECCIÓN")
    logger.info(f"{'='*60}\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        inspect_credit(sys.argv[1])
    else:
        tid = input("Ingrese el ID del crédito a inspeccionar (ej: 5431000350002): ")
        if tid.strip():
            inspect_credit(tid)
