# Guía de exportación SIH

Esta guía documenta el módulo de exportación SIH de Aforix.

El módulo SIH transforma mediciones procesadas por Aforix en archivos CSV con la estructura esperada por SIH. Por cada medición seleccionada genera los CSV de actuaciones y aforos; en el CSV de aforos también incluye los campos IVE cuando el cálculo está disponible. Además, genera un informe Excel complementario con el detalle del cálculo cuando puede preparar los datos normalizados:

```text
ID_{export_id}_actuacion_{station_id}_{YYYYMMDD}_{HHMMSS}.csv
ID_{export_id}_aforo_{station_id}_{YYYYMMDD}_{HHMMSS}.csv
```

Además genera un archivo de metadata/log:

```text
sih_export_metadata.csv
```

## 1. Objetivo general

El objetivo del módulo SIH es exportar aforos ya procesados por Aforix hacia el formato requerido por SIH.

El módulo no ingesta archivos raw ni normaliza datos. Trabaja sobre:

- datos normalizados en `database/normalized`;
- datos raw canonical en `database/raw_canonical`, cuando están disponibles;
- lookups CSV en `configs/sih`;
- configuración declarativa en `configs/sih/sih.yaml`;
- un archivo de selección batch, por defecto `configs/sih/selection_template.csv`, o un selection file temporal generado por el modo interactivo.

Dentro del pipeline de Aforix, SIH se ubica al final:

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> export/sih
```

## 2. Qué genera

Por cada fila válida del archivo de selección, el módulo intenta generar:

| Archivo o campos | Contenido |
| --- | --- |
| `ID_{export_id}_actuacion_*.csv` | registro para tabla SIH de actuaciones |
| `ID_{export_id}_aforo_*.csv` | registro para tabla SIH de aforos; incluye `incertidumbre_IVE`, `error_IVE` y `calidad_IVE` |
| `IVE_{instrumento}_{estacion}_{fecha}_{hora}.xlsx` | informe complementario con resumen, parámetros, puntos normalizados y detalle IVE, si los datos permiten preparar el cálculo |

Al final de la corrida siempre escribe:

```text
outputs/sih/sih_export_metadata.csv
```

La metadata permite auditar qué filas se exportaron correctamente y cuáles fallaron.

### 2.1 Cálculo de IVE en la exportación SIH

Para cada medición seleccionada, la exportación intenta calcular IVE desde `Points.csv` normalizado. Busca el archivo en este orden:

```text
database/normalized/{instrument}/Points.csv
database/normalized/{instrument}/Points/Points.csv
database/normalized/Points.csv
```

Filtra por `station_id`, `measurement_date` y `measurement_time`; si el archivo incluye la columna `instrument`, también filtra por instrumento. Para un archivo compartido en la raíz de normalized, incluye esa columna para distinguir instrumentos. Requiere `distance_m`, `depth_m`, `velocity_mean_m_s` y un único `width_m` positivo. Los valores numéricos incompletos, las distancias duplicadas o fuera de la sección y las profundidades negativas impiden preparar el cálculo.

El motor ordena las verticales por distancia y aplica el método de integración *mid-section*:

```text
Q_mid = Σ (ancho_mid_i × profundidad_i × velocidad_i)
```

Si los puntos no incluyen los bordes físicos en `x=0` o `x=width_m`, el motor agrega nodos sintéticos con profundidad y velocidad cero. Para SIH, los modos configurados en `configs/sih/sih.yaml` son:

```yaml
sih:
  ive:
    borders:
      left: zero
      right: preserve_depth
```

`zero` fija profundidad y velocidad en cero; `preserve_depth` conserva la profundidad de un borde medido y fija su velocidad en cero; `preserve_both` conserva ambas. Los nodos sintéticos siempre quedan en cero. Los bordes físicos no cuentan dentro del número de verticales para determinar aplicabilidad: se requieren al menos **10 verticales interiores**.

El cálculo combina cuatro componentes de incertidumbre independientes: sistemática, ancho, profundidad y velocidad. Con los parámetros actuales del motor, la componente sistemática relativa es 1 %, la componente de ancho es 0,5 % por vertical y la desviación estándar de profundidad utilizada es `max(s_d,IVE, 0,01 m)`. Para velocidad se usa directamente `s_v,IVE`, sin aplicar un mínimo instrumental `s_v,min`. La incertidumbre absoluta es la raíz de la suma de las varianzas de esos componentes; la relativa se obtiene como `100 × u_Q / |Q_mid|`.

La calidad se clasifica según la incertidumbre relativa: `Excelente` hasta 2 %, `Buena` hasta 5 %, `Regular` hasta 8 % y `Mala` por encima de 8 %. Esta decisión metodológica y sus limitaciones se explican en [`docs/IVE_METHODOLOGY_DECISIONS.md`](IVE_METHODOLOGY_DECISIONS.md). El estado `calculated` describe el resultado del método implementado; no certifica por sí solo conformidad con una norma externa.

### Estados y efecto en la exportación

| Estado | Significado y salida |
| --- | --- |
| `calculated` | Se calculan incertidumbre absoluta, relativa y calidad; se escriben en el CSV de aforos y en el informe Excel. |
| `not_applicable` | Hay menos de 10 verticales interiores. Los campos numéricos IVE quedan vacíos; la calidad informa que no aplica. |
| `not_available` | No se obtiene un resultado, por ejemplo por caudal nulo. Los campos numéricos quedan vacíos y la metadata registra el motivo. |

Si faltan puntos o sus datos no permiten preparar IVE, la exportación SIH de actuaciones y aforos igualmente continúa: la metadata deja constancia del estado y del motivo, y no se crea el informe Excel IVE de esa medición. Cuando el cálculo sí se prepara, el informe se guarda en `outputs/sih/incertidumbre/` con hojas `Resumen`, `Parametros`, `Points_normalizados` y `Detalle_IVE`. Es un informe de trazabilidad con valores del motor; no recalcula el modelo mediante fórmulas de Excel.

## 3. Arquitectura general

El flujo interno actual es:

1. Cargar `configs/sih/sih.yaml`.
2. Resolver rutas relativas al repo.
3. Definir el archivo de selección:
   - en modo batch: usar `--selection-file` o `configs/sih/selection_template.csv`;
   - en modo interactivo: construir automáticamente un CSV temporal en `outputs/sih/`.
4. Cargar los lookups configurados.
5. Para cada fila de selección:
   - identificar instrumento;
   - cargar `Summary` normalizado;
   - cargar `Summary` raw canonical si existe;
   - resolver la medición por `station_id`, `measurement_date`, `measurement_time`;
   - construir fecha/hora de medición;
   - resolver `id_estacion`;
   - resolver `id_instrumento` mediante lookup configurable;
   - resolver `id_tipo_aforo`;
   - resolver `id_instrumentos_rangos`;
   - construir fila `sdh_actuaciones`;
   - construir fila `sdh_aforos`;
   - escribir CSVs de salida;
   - registrar metadata.
6. Escribir `sih_export_metadata.csv`.

Los detalles de configuración están en `docs/SIH_CONFIGURATION.md` y el matching de instrumentos se explica en `docs/SIH_MATCHING.md`.

## 4. Estructura de carpetas

### 4.1 Código fuente

```text
src/aforix/export/sih/
```

Archivos principales:

| Archivo | Rol |
| --- | --- |
| `cli.py` | CLI interna del módulo |
| `config.py` | carga de YAML y resolución de rutas |
| `interactive.py` | flujo interactivo y generación de selection CSV temporal |
| `runner.py` | orquestación de la exportación batch |
| `inputs.py` | lectura de selección, normalized y raw canonical |
| `mappings.py` | construcción de filas SIH y resolución de lookups |
| `io.py` | lectura robusta de CSVs |
| `writers.py` | escritura de CSVs y metadata |
| `schema.py` | columnas de salida SIH |
| `ive_points.py` | localiza y valida los puntos de una medición en `Points.csv` |
| `ive_integration.py` | conecta los puntos normalizados con el cálculo IVE y el informe Excel |
| `validation.py` | reservado para validaciones futuras |

El motor matemático está en `src/aforix/analysis/uncertainty/calculator.py`; la clasificación por incertidumbre y el umbral de aplicabilidad están en `ive.py`, y el libro de trazabilidad se escribe desde `excel_report.py`.

### 4.2 Configuración SIH

```text
configs/sih/
```

Archivo principal:

```text
configs/sih/sih.yaml
```

Archivos CSV referenciados por configuración:

```text
configs/sih/instrumentos.csv
configs/sih/tipos_aforos.csv
configs/sih/instrumentos_rangos.csv
configs/sih/selection_template.csv
```

El código también define un default para:

```text
configs/sih/estaciones.csv
```

pero el `sih.yaml` actual no lo lista explícitamente en `lookup_files`.

### 4.3 Datos de entrada

```text
database/normalized/
database/raw_canonical/
```

### 4.4 Salidas

Por defecto:

```text
outputs/sih/
```

## 5. Comandos CLI

### 5.1 Export simple usando defaults

```bash
aforix export sih -c configs/examples/main.yaml
```

Este comando usa por defecto:

```text
--sih-config configs/sih/sih.yaml
--selection-file configs/sih/selection_template.csv
```

### 5.2 Export con SIH config explícita

```bash
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml
```

### 5.3 Export con selection file explícito

```bash
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml --selection-file configs/sih/selection_template.csv
```

### 5.4 Ejemplo Windows multilínea

```bat
aforix export sih ^
  -c configs/examples/main.yaml ^
  --sih-config configs/sih/sih.yaml ^
  --selection-file configs/sih/selection_template.csv
```

### 5.5 Modo interactivo desde CLI de Aforix

```bash
aforix export sih -c configs/examples/main.yaml --interactive
```

En este modo, Aforix detecta mediciones disponibles desde `database/normalized`, pregunta qué exportar, genera un CSV temporal de selección y luego reutiliza el mismo runner batch.

### 5.6 Modo interactivo directo con `python -m`

Comando solicitado para ejecución directa del módulo:

```bat
python -m aforix.export.sih.cli ^
  -c configs/examples/main.yaml ^
  --sih-config configs/sih/sih.yaml ^
  --interactive
```

Argumentos:

| Argumento | Significado |
| --- | --- |
| `python -m aforix.export.sih.cli` | ejecuta directamente la CLI interna del módulo SIH |
| `-c configs/examples/main.yaml` | ruta al YAML principal de Aforix; se recibe por compatibilidad de CLI |
| `--sih-config configs/sih/sih.yaml` | ruta al YAML específico del módulo SIH |
| `--interactive` | activa el flujo interactivo |

Ejecutar desde la raíz del repositorio, donde existen `configs/`, `database/`, `src/` y `pyproject.toml`.

## 6. Modo batch vs modo interactivo

### 6.1 Modo batch

Usar batch cuando ya se sabe exactamente qué mediciones exportar.

Entrada principal:

```text
configs/sih/selection_template.csv
```

Ventajas:

- reproducible;
- adecuado para exportaciones masivas;
- fácil de versionar;
- permite control exacto de `export_id`.

### 6.2 Modo interactivo

Usar interactivo cuando el usuario quiere explorar mediciones disponibles y seleccionar desde consola.

Ventajas:

- no requiere escribir manualmente el selection file;
- detecta instrumentos y estaciones desde normalized;
- muestra preview de mediciones;
- genera `export_id` automáticamente;
- usa el mismo runner batch, por lo que no duplica lógica de exportación.

## 7. Flujo interactivo completo

El modo interactivo sigue estos pasos reales:

1. Carga `configs/sih/sih.yaml`.
2. Lee `sih.inputs.normalized_input_dir`.
3. Lee `sih.output.output_dir`.
4. Recorre los instrumentos configurados en `sih.instruments`.
5. Omite instrumentos con `enabled: false`.
6. Para cada instrumento habilitado intenta cargar `Summary` normalizado.
7. Verifica que existan las columnas requeridas:
   - `station_id`;
   - `measurement_date`;
   - `measurement_time`.
8. Normaliza fechas y horas para selección.
9. Muestra instrumentos disponibles.
10. Permite seleccionar uno, varios o todos.
11. Muestra estaciones disponibles según instrumentos seleccionados.
12. Permite seleccionar una, varias o todas.
13. Pide fecha inicial y final en formato `YYYYMMDD`.
14. Filtra mediciones.
15. Ordena por `instrument`, `station_id`, `measurement_date`, `measurement_time`.
16. Muestra preview de mediciones.
17. Permite exportar todas las listadas o seleccionar índices específicos.
18. Pide prefijo de `export_id`.
19. Genera `export_id` automático.
20. Muestra resumen de exportación.
21. Pide confirmación final.
22. Escribe un selection CSV temporal en `outputs/sih/`.
23. Ejecuta el runner batch normal con ese selection file.
24. Genera CSVs SIH y metadata.

## 8. Detección automática desde normalized

El modo interactivo carga mediciones desde:

```text
database/normalized/{instrument}/Summary.csv
database/normalized/{instrument}/Summary/Summary.csv
database/normalized/Summary.csv
```

La raíz `database/normalized` viene de:

```yaml
sih:
  inputs:
    normalized_input_dir: database/normalized
```

Columnas mínimas requeridas para que un instrumento aparezca en modo interactivo:

```text
station_id
measurement_date
measurement_time
```

Si faltan columnas, el instrumento se omite y se imprime un mensaje del tipo:

```text
Instrumento omitido por columnas faltantes: molinete (['measurement_time'])
```

El preview puede incluir además:

```text
q_total_m3s
q_total_ls
```

si esas columnas existen.

## 9. Formatos de fecha y hora

### 9.1 Fecha

El modo interactivo normaliza fechas quitando guiones y barras.

Ejemplos:

```text
20260119 -> 20260119
2026-01-19 -> 20260119
2026/01/19 -> 20260119
19/01/2026 -> 20260119
01/19/2026 -> 20260119
```

Formato recomendado para selección SIH:

```text
YYYYMMDD
```

### 9.2 Hora

El modo interactivo normaliza horas quitando `:` y `.`. Si el valor resultante es numérico, aplica zero-padding a 6 dígitos:

```text
14:18:00 -> 141800
14.18.00 -> 141800
94521 -> 094521
094521 -> 094521
```

Este punto es importante porque durante el desarrollo se detectaron diferencias entre instrumentos: algunas mediciones, especialmente en Molinete u hojas editadas manualmente, pueden producir horas sin cero inicial (`94521`) mientras otros instrumentos generan `094521`.

Recomendación actual:

```text
measurement_date -> YYYYMMDD
measurement_time -> HHMMSS
```

## 10. Selection file temporal generado automáticamente

El modo interactivo genera un CSV temporal dentro de:

```text
outputs/sih/
```

Nombre:

```text
_interactive_selection_{YYYYMMDD}_{HHMMSS}.csv
```

Estructura:

```text
station_id
measurement_date
measurement_time
instrument
export_id
```

Ejemplo:

```csv
station_id,measurement_date,measurement_time,instrument,export_id
7001,20241219,214313,nivus,EXP001
7071,20260120,142300,molinete,EXP002
```

El `station_id` del selection file es autoritativo y debe coincidir exactamente con el valor normalizado. No se aplican alias semánticos del tipo `P<n> -> 7000+n`.

Este archivo es importante porque:

- deja trazabilidad de la selección interactiva;
- permite reproducir una exportación;
- puede reutilizarse luego con `--selection-file`;
- conecta el modo interactivo con el mismo runner batch.

## 11. Export_id automático

El modo interactivo pide:

```text
Prefijo export_id (Enter = EXP):
```

Si el usuario presiona Enter, usa:

```text
EXP
```

Luego genera IDs secuenciales con tres dígitos:

```text
EXP001
EXP002
EXP003
```

Si el usuario ingresa `SIH`, se generan:

```text
SIH001
SIH002
SIH003
```

El orden sigue el orden final de las mediciones seleccionadas.

## 12. Ejemplo completo de sesión interactiva

```text
Aforix — SIH interactive export
================================
Normalized input: D:\repos\aforix\database\normalized
Output directory: D:\repos\aforix\outputs\sih

Instrumentos disponibles
[1] flowtracker
[2] molinete
[3] nivus
[A] Todos
Seleccione valores separados por coma: 2,3

Estaciones disponibles
[1] 7001
[2] 7071
[3] 7008
[A] Todos
Seleccione valores separados por coma: 1,2

Fecha inicial YYYYMMDD (Enter = sin límite): 20251201
Fecha final   YYYYMMDD (Enter = sin límite): 20260131

Mediciones encontradas:
[1] station_id=7001 | measurement_date=20241219 | measurement_time=214313 | instrument=nivus | q_total_m3s=0.075591
[2] station_id=7071 | measurement_date=20260120 | measurement_time=142300 | instrument=molinete

Exportar todas las mediciones listadas? [s/N]: s

Prefijo export_id (Enter = EXP): SIH

Resumen de exportación
Mediciones: 2
Instrumentos: molinete, nivus
Estaciones: 7071, 7001

Continuar con la exportación? [s/N]: s

Selection file generado: D:\repos\aforix\outputs\sih\_interactive_selection_20260506_231500.csv

Aforix — SIH export
====================
Output directory: D:\repos\aforix\outputs\sih
Generated files: 7
 - D:\repos\aforix\outputs\sih\ID_SIH001_actuacion_7001_20241219_214313.csv
 - D:\repos\aforix\outputs\sih\ID_SIH001_aforo_7001_20241219_214313.csv
 - D:\repos\aforix\outputs\sih\incertidumbre\IVE_nivus_7001_20241219_214313.xlsx
 - D:\repos\aforix\outputs\sih\ID_SIH002_actuacion_7071_20260120_142300.csv
 - D:\repos\aforix\outputs\sih\ID_SIH002_aforo_7071_20260120_142300.csv
 - D:\repos\aforix\outputs\sih\incertidumbre\IVE_molinete_7071_20260120_142300.xlsx
 - D:\repos\aforix\outputs\sih\sih_export_metadata.csv
```

## 13. Inputs normalizados requeridos

El módulo carga `Summary` normalizado. Para cada instrumento busca en este orden:

```text
database/normalized/{instrument}/Summary.csv
database/normalized/{instrument}/Summary/Summary.csv
database/normalized/Summary.csv
```

Si la tabla tiene columna `instrument`, se filtra por el instrumento de la fila de selección.

Columnas usadas actualmente desde normalized:

| Uso SIH | Configurado en `normalized_fields` | Ejemplo de columna normalized |
| --- | --- | --- |
| ancho | `ancho` | `width_total_m` |
| caudal | `caudal` | `q_total_m3s` |
| profundidad | `profundidad` | `depth_mean_m` |
| sección | `seccion` | `area_total_m2` |
| velocidad media | `velocidad_media` | `velocity_mean_m_s` |
| fecha inicio | `fecha_inicio` | fecha y hora de medición del `Summary` |
| fecha fin | `fecha_fin` | fuente específica por instrumento |
| operador | `id_operador` | `operador`, formateado para SIH: iniciales, abreviatura o primer token según el formato |
| lectura de escala de actuación | `lectura_escala` | `escala_inicio` |
| escalas de aforo | `escala_inicio`, `escala_fin` | campos normalizados en `Summary` |

El matching de medición usa:

```text
station_id
measurement_date
measurement_time
```

## 14. Inputs raw canonical requeridos

El raw canonical es opcional, pero muchos campos SIH dependen de él. Se busca `Summary` raw canonical en el mismo patrón:

```text
database/raw_canonical/{instrument}/Summary.csv
database/raw_canonical/{instrument}/Summary/Summary.csv
database/raw_canonical/Summary.csv
```

Si no se encuentra, el módulo puede continuar, pero campos como observaciones, radio hidráulico o matching de instrumento pueden quedar vacíos o fallar según configuración. Operador, escalas y fechas de inicio/fin se leen desde el Summary normalizado.

La metadata registra:

```text
raw_canonical_found = True/False
```

## 15. Salidas SIH

### 15.1 Actuaciones

Columnas actuales de `sdh_actuaciones`:

```text
id
id_estacion
id_operador
id_tipo_actuacion
id_instrumento
fecha
pendiente
relevante
lectura_escala
observaciones
```

### 15.2 Aforos

Columnas actuales de `sdh_aforos`:

```text
ancho
caudal
escala_fin
escala_inicio
escala_media
fecha_fin
fecha_inicio
id
id_actuacion
id_estacion
id_instrumento
id_instrumentos_rangos
id_perfil
id_tipo_aforo
observaciones
profundidad
seccion
velocidad_media
radio_hidraulico
nivel_confiabilidad
incertidumbre_IVE
error_IVE
calidad_IVE
```

`incertidumbre_IVE` contiene la incertidumbre relativa en porcentaje; `error_IVE`, la absoluta en m³/s; `calidad_IVE`, la clasificación o el mensaje de no disponibilidad/no aplicabilidad.

Los IDs autogenerados por SIH se exportan vacíos en el estado actual del código.

## 16. Metadata de exportación

El módulo genera:

```text
outputs/sih/sih_export_metadata.csv
```

Para exportaciones exitosas incluye campos como:

```text
status
export_id
instrument
station_id
measurement_date
measurement_time
normalized_source
raw_canonical_found
actuaciones_file
aforos_file
ive_report_file
ive_report_error
ive_status
ive_reason
```

`ive_status` y `ive_reason` permiten revisar el resultado IVE por medición; `ive_report_file` señala el libro generado y `ive_report_error` registra por qué no se pudo crear.

Para errores de exportación incluye:

```text
status
export_id
instrument
station_id
measurement_date
measurement_time
error
```

Valores de `status`:

| status | Significado |
| --- | --- |
| `success` | se generaron los dos CSV de salida |
| `error` | falló la exportación de esa fila |

## 17. Relación con otros documentos

- Configuración SIH: `docs/SIH_CONFIGURATION.md`
- Matching de instrumentos: `docs/SIH_MATCHING.md`
- Solución de problemas: `docs/SIH_TROUBLESHOOTING.md`
- Cálculo IVE y decisión metodológica: `docs/IVE_METHODOLOGY_DECISIONS.md`

## 18. Limitaciones actuales documentadas

Según el estado actual del código:

- `quality_input_dir` existe en YAML, pero la integración con quality metrics no está usada todavía en la construcción de filas;
- `validation.py` es un placeholder para validaciones futuras;
- el matching de fechas/hora tolera algunos formatos en normalized, pero conviene estandarizar a `YYYYMMDD` y `HHMMSS`;
- los CSV de lookups deben existir en las rutas configuradas para que la exportación funcione.
