# Generador de Flujos Proyectados

Este proyecto es una herramienta desarrollada en Python diseñada para calcular y proyectar los flujos de caja futuros (amortizaciones e intereses) de un portafolio de créditos, basándose en la información contenida en varios archivos de origen y aplicando reglas de negocio financieras específicas.

## Requisitos Previos

1. Tener instalado **Python 3.8+**.
2. Instalar las dependencias necesarias. Puede hacerlo ejecutando el siguiente comando en la terminal:
   ```bash
   pip install pandas openpyxl xlrd python-dateutil
   ```

## Estructura de Archivos de Entrada

La herramienta espera leer 5 archivos de entrada ubicados en la carpeta principal (la misma donde se encuentra `main.py`). Los nombres deben ser los siguientes (configurable en `config/settings.py`):

1. **Consulta oracle 30-04-2026.xls**: Archivo principal que contiene los datos del crédito, saldos, tipo de tasa (fija/variable) y márgenes de valor. Aunque tiene extensión `.xls`, el sistema lo lee automáticamente como archivo de texto delimitado por tabulaciones.
2. **proy_inventario_perfil.xls**: Contiene la estructura general del crédito, periodicidades de pago de interés y el tipo de amortización (1=Anual, 2=Semestral, 12=Mensual, ND=Flujo irregular).
3. **proy_consulta_guias.xls**: Archivo esencial para los intereses. Determina la `FECHA INICIAL INTERES`, la fecha final, y el `METODO CONTEO` de días (Ej: Actual/360, 30E/360, etc).
4. **Tasas_forward.xlsx**: (Excel binario) Archivo histórico y proyectado de las tasas variables o índices (ej. ISOR, LUS3, etc.).
5. **tabla_nd.xlsx**: (Excel binario) Tabla con la distribución exacta de porcentajes de pago (`% Real`) para los créditos con amortizaciones irregulares (`ND`).

## Uso y Ejecución

Para iniciar el procesamiento y generar el flujo, abra una terminal en el directorio raíz del proyecto y ejecute:

```bash
python main.py
```

### ¿Qué hace el sistema durante la ejecución?
1. **Lectura Segura:** Escanea los archivos `.xls`, intentando leerlos nativamente como delimitados (Maneja codificaciones especiales `latin-1`, `utf-8`).
2. **Depuración:** Filtra únicamente aquellos créditos cuyo saldo `SDO_US` es mayor a 0.
3. **Generación de ID:** Estandariza un identificador combinando la cuenta del crédito y el tramo (`COD_CREDITO` + "000" + `NUM_TRAMO`).
4. **Validaciones en consola:** Realiza una revisión de calidad (fechas nulas, periodicidades extrañas, tasas faltantes) y emite `WARNINGS` en la terminal sin detener el proceso.
5. **Cálculo de Amortizaciones:** Utilizando el `SDO_US` del archivo de Oracle, distribuye matemáticamente el saldo según las fechas generadas. Para los créditos "ND", mapea la `tabla_nd` y normaliza los porcentajes para que siempre sumen el 100% de la deuda.
6. **Cálculo de Intereses:** Con base en la `FECHA INICIAL INTERES` de las guías, se determina la periodicidad y días reales transcurridos aplicando los métodos de conteo. Se suma la tasa Forward y el `MARGEN_VALOR`.

## Resultados (Output)

Al finalizar sin errores críticos, el programa generará un archivo de salida en el mismo directorio con el nombre:

**`flujo_proyectado.xlsx`**

Este archivo contiene la consolidación del flujo de amortizaciones e intereses. Sus columnas principales son:
* `COD_CREDITO`: El código original del crédito.
* `MDA_TR`: La moneda en la que se calculó.
* `PMISTA`: Fuente o pagador.
* `fecha_operacion`: Línea de tiempo unificada (fusiona las fechas en las que caen las amortizaciones y las fechas específicas de los intereses).
* `pago_amortizacion`: El monto de capital abonado para ese periodo (normalizado a SDO_US).
* `pago_interes`: El monto de interés calculado con la fórmula de la tasa vigente por el factor de conteo de días en base al saldo insoluto remanente.

## Modificaciones de Configuración
Si el nombre de los archivos de origen cambia, o se requiere cambiar la fecha de corte, usted puede editar de forma segura el archivo `config/settings.py`.
