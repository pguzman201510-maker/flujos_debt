# Metodología de Cálculo de Intereses

El motor de cálculo de intereses (`modules/interest_engine.py`) procesa el flujo de pagos futuros analizando la configuración de cada crédito (tasa fija o variable, fuente de fondeo, fechas y convenciones de días). A continuación se documenta el árbol de decisiones y las fórmulas matemáticas empleadas en el sistema.

---

## 1. Definición de la Tasa Base y Márgenes (`MARGEN VALOR`)

El sistema utiliza una jerarquía para extraer el margen (o spread) con la mayor precisión decimal posible, evitando errores por redondeos de plataformas:
1. **Prioridad 1:** Archivo `proy_inventario_perfil.xls` (columna `MARGEN VALOR`). Proporciona alta precisión.
2. **Prioridad 2:** Archivo `proy_consulta_guias.xls`. Solo se utiliza si el inventario carece del dato o si literalmente indica la etiqueta `"GUIA"`.
3. **Prioridad 3:** Archivo `Consulta oracle 30-04-2026.xls`. Usado como último recurso. Debido a que Oracle a veces guarda tasas en formatos inflados (ej. `4.8` en vez de `0.048`), el sistema aplica un factor de conversión `/100` inteligente si detecta que la cifra entera supera la unidad lógica.

---

## 2. Tipos de Tasa: Fija vs. Variable

El cálculo base de la tasa anual (`base_annual_rate`) depende de la columna `CLASE_INT` reportada en Oracle:

### 2.1 Tasas Fijas
Se consideran **fijas** las clases que se encuentran dentro de las definiciones preestablecidas (configurable en `config/settings.py` como `FIXED_RATE_CODES`, por ejemplo: `FUFI`, `FIJA`, `SINI`, `FI19`).

**Cálculo:**
- La tasa base es estrictamente igual al `MARGEN VALOR` (ya expresado en decimales, ej: `0.041` = 4.1%).
- `base_annual_rate = MARGEN VALOR`

### 2.2 Tasas Variables e Indexadas (Forward)
Para créditos no fijos (por ejemplo, aquellos anclados a `ISOR`, `LUS3`, etc.), la tasa fluctúa en el tiempo consultando el archivo `Tasas_forward.xlsx`.

**Cálculo Estándar Variable:**
1. Se localiza la tasa base (Forward) intersecando la fecha futura del pago contra el índice correspondiente (`CLASE_INT`).
2. Se convierte el indicador a porcentaje numérico (`Forward / 100`).
3. Se adiciona el `MARGEN VALOR` al resultado.
- `base_annual_rate = (Forward / 100) + MARGEN VALOR`

---

## 3. Condiciones Especiales y Primas por Acreedor (`PMISTA`)

Existen escenarios excepcionales condicionados por la columna `PMISTA`.

### 3.1 Margen Adicional para `BID`
Para los créditos cuyo acreedor (`PMISTA`) es **`BID`** **y su tasa sea variable**, se adiciona un margen regulatorio (`MBID_RATE`, parametrizable en `config/settings.py`, por defecto `0.80%`).
* `base_annual_rate = base_annual_rate + 0.0080`

---

## 4. Columnas de Auditoría y Verificación

Para facilitar la auditoría de los cálculos y permitir la validación manual contra herramientas externas (como Excel), el sistema exporta columnas adicionales:

* **`valor_indice`**: El valor crudo extraído de `Tasas_forward.xlsx` (en decimal, ej: `0.0244`).
* **`margen_aplicado`**: El `MARGEN VALOR` detectado para el periodo.
* **`tasa_aplicada`**: Representa la tasa efectiva del periodo:
  * Para **Tasas Variables**: Es la tasa de periodo (`base_annual_rate / Frecuencia`).
  * Para **Tasas Fijas**: Es la tasa nominal anual (`base_annual_rate`).

---

## 5. Sensibilidad (Choques)

Si el usuario ejecuta la herramienta en modo interactivo (`sensibilidad.py`), puede inyectar un escenario de estrés (`shock_int`). Este estrés es un sumatorio plano porcentual:
* `base_annual_rate = base_annual_rate + (shock_int / 100)`

*(Ejemplo: Un choque de `+1.5%` sumará `0.015` directo a la tasa nominal).*

---

## 6. Aplicación Final: Factor de Tiempo vs Frecuencia

Para obtener el cobro real de la cuota (`pago_interes`), la tasa de interés anual debe convertirse en una tasa de periodo y multiplicarse por el capital.

**La fórmula general es:  `Interés = Saldo Insoluto × Tasa × Factor`**

Las reglas matemáticas para obtener este factor cambian según la naturaleza de la tasa:

### A. Metodología para Tasas Variables (Frecuencia Directa)
Por reglas de negocio directas, las tasas variables ignoran los cálculos convencionales de conteo de días calendario y basan el cobro en fracciones directas según la frecuencia de amortización estipulada en `proy_consulta_guias.xls`.
* **Fórmula:** `Factor = 1.0 / Frecuencia`
* *Ejemplo:* Si el pago es semestral (`Frecuencia = 2`), el `Factor` es `1.0 / 2 = 0.5`.
* *Resultado:* `Pago Interés = Saldo Insoluto × base_annual_rate × 0.5`

### B. Metodología para Tasas Fijas (Convenciones de Conteo de Días)
Las tasas fijas aplican factores dinámicos evaluando los días calendario exactos transcurridos desde el pago anterior, empleando la convención especificada en la columna `METODO CONTEO` de guías:

* **0: 30/360 (US)**: Estima meses de 30 días, limitando el día 31.
* **1: 365/365 (Actual/365)**: Días calendario transcurridos divididos entre 365.
* **2: Actual/360**: Días calendario reales divididos en un modelo contable de 360 días.
* **3: Actual/365**: (Equivalente al #1) Días reales sobre 365.
* **4: Actual/365 ajustado**: (Equivalente al #1).
* **5: 30E/360 (Europeo)**: Estándar europeo para meses contables de 30 días, sin importar la interdependencia del día inicial.

Para todos los métodos fijos el cálculo resultante es:
* `Factor = Días_Del_Periodo / Base_Anual (360 o 365)`
* *Resultado:* `Pago Interés = Saldo Insoluto × base_annual_rate × Factor`

---

## 7. Jerarquía de Amortización y Manejo de Errores

El motor de amortización (`modules/calendar_generator.py`) determina las fechas de pago siguiendo esta jerarquía:
1. **Bullet Directo**: Si `FECHA PRIMER PAGO` es igual a `FECHA VENCIMIENTO`, o si faltan datos de periodicidad pero las fechas coinciden, se asume un pago único al final.
2. **Tablas Irregulares (ND)**: Si el tipo es `ND` o si la celda está **vacía** (pero no es Bullet), se busca el `ID_CREDITO` en `tabla_nd.xlsx`.
3. **Periodicidad Estándar**: Si no es irregular, se usan los códigos `1` (Anual), `2` (Semestral) o `12` (Mensual).
4. **Fallback de Intereses**: Si la periodicidad de amortización está vacía, se intenta heredar la periodicidad de pago de intereses.

### Reporte de Inconsistencias (`errores_proyeccion.txt`)
El sistema genera automáticamente un archivo de texto con los créditos que presentaron problemas, incluyendo instrucciones de solución:
* **FECHAS_INCORRECTAS**: Créditos donde la fecha de vencimiento es anterior a la de inicio (`ULT_PAGO < PRIM_PAGO`).
* **ND_NO_ENCONTRADO**: Créditos marcados como `ND` que no existen en la tabla auxiliar.
* **ND_TRAMO_FALTANTE_PERO_CODIGO_EXISTE**: Cuando el tramo específico no está en `tabla_nd` pero el código base sí.
* **AMORTIZACION_VACIA_NO_BULLET**: Créditos sin tipo de amortización que no pudieron ser resueltos como Bullet.
* **ALINEACION_FECHAS_INCORRECTA**: Créditos donde el ciclo periódico no aterriza exactamente en el vencimiento final.
* **SALDO_CERO_O_NEGATIVO**: Créditos con saldo en USD reportado como cero o negativo (se omiten de la proyección).
* **FALTA_EN_INVENTARIO**: Créditos reportados en Oracle que no existen en el archivo de Inventario Perfil.
* **VENCIMIENTO_MUY_LEJANO**: Créditos con vencimientos superiores a 60 años (posibles errores de digitación).
* **INDICE_FALTANTE**: Créditos de tasa variable cuyo índice no tiene proyecciones en `Tasas_forward.xlsx`.
* **TASA_FUERA_DE_RANGO**: Periodos donde la tasa anual calculada es negativa o superior al 15%.
* **GAP_EN_GUIAS**: Fechas de pago que no están cubiertas por ningún rango de fecha en las Guías de Interés.
* **GUIA_VENCE_ANTES_QUE_CAPITAL**: Cuando la última guía definida vence antes que el capital del crédito.
