#!/bin/bash

echo "==============================================="
echo "INICIANDO PIPELINE DE PROYECCIÓN DE FLUJOS"
echo "==============================================="

# 1. Check dependencies
if ! python3 -c "import pandas" &> /dev/null; then
    echo "(!) Error: Pandas no está instalado. Ejecute 'pip install pandas openpyxl xlrd'"
    exit 1
fi

# 2. Run Main Projection
echo -e "\n[1/3] Generando proyección de flujos..."
python3 main.py

if [ $? -eq 0 ]; then
    echo "✔ Proyección completada exitosamente."
    echo "  > Archivo generado: flujo_proyectado.xlsx"
else
    echo "✖ Error durante la proyección."
    exit 1
fi

# 3. Check Error Report
if [ -f "errores_proyeccion.txt" ]; then
    echo -e "\n[2/3] Verificando reporte de inconsistencias..."
    ERR_COUNT=$(grep -c "ID:" errores_proyeccion.txt)
    echo "  > Se encontraron $ERR_COUNT inconsistencias en los datos."
    echo "  > Revise 'errores_proyeccion.txt' para ver las instrucciones de solución."
fi

# 4. Optional Sensitivity Reminder
echo -e "\n[3/3] Proceso finalizado."
echo "Si desea realizar un análisis de estrés, ejecute: python3 sensibilidad.py"
echo "Si desea auditar un crédito específico, ejecute: python3 inspect_credit.py <ID>"
echo "==============================================="
