# Guía de exportación SIH

Esta guía documenta el módulo de exportación SIH de Aforix.

El módulo SIH transforma mediciones procesadas por Aforix en archivos CSV con la estructura esperada por SIH. Actualmente genera dos archivos por medición seleccionada:

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
- un archivo de selección batch, por defecto `configs/sih/selection_template.csv`.

Dentro del pipeline de Aforix, SIH se ubica al final:

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> export/sih
```

## 2. Qué genera

Por cada fila válida del archivo de selección, el módulo intenta generar:

| Archivo | Contenido |
| --- | --- |
| `ID_{export_id}_actuacion_*.csv` | registro para tabla SIH de actuaciones |
| `ID_{export_id}_aforo_*.csv` | registro para tabla SIH de aforos |

Al final de la corrida siempre escribe:

```text
outputs/sih/sih_export_metadata.csv
```

La metadata permite auditar qué filas se exportaron correctamente y cuáles fallaron.

## 3. Arquitectura general

El flujo interno actual es:

1. Cargar `configs/sih/sih.yaml`.
2. Resolver rutas relativas al repo.
3. Cargar el archivo de selección.
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
| `runner.py` | orquestación de la exportación |
| `inputs.py` | lectura de selección, normalized y raw canonical |
| `mappings.py` | construcción de filas SIH y resolución de lookups |
| `io.py` | lectura robusta de CSVs |
| `writers.py` | escritura de CSVs y metadata |
| `schema.py` | columnas de salida SIH |
| `validation.py` | reservado para validaciones futuras |

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

### 5.5 Modo interactivo

El CLI acepta:

```bash
aforix export sih -c configs/examples/main.yaml --interactive
```

Según el estado actual del código, el flag `--interactive` se transmite al runner, pero el runner actual sigue cargando el archivo de selección. No hay todavía un flujo interactivo completo implementado para elegir mediciones desde consola. Documentar esto es importante para evitar confusión: por ahora el uso operativo recomendado es batch con `selection_file`.

## 6. Inputs normalizados requeridos

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
| fecha inicio | `fecha_inicio_date/time` | `measurement_date`, `measurement_time` |
| fecha fin | `fecha_fin_date/time` | `measurement_date`, `measurement_time` |

El matching de medición usa:

```text
station_id
measurement_date
measurement_time
```

## 7. Inputs raw canonical requeridos

El raw canonical es opcional, pero muchos campos SIH dependen de él. Se busca `Summary` raw canonical en el mismo patrón:

```text
database/raw_canonical/{instrument}/Summary.csv
database/raw_canonical/{instrument}/Summary/Summary.csv
database/raw_canonical/Summary.csv
```

Si no se encuentra, el módulo puede continuar, pero campos como operador, observaciones, escalas, radio hidráulico o matching de instrumento pueden quedar vacíos o fallar según configuración.

La metadata registra:

```text
raw_canonical_found = True/False
```

## 8. Salidas SIH

### 8.1 Actuaciones

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

### 8.2 Aforos

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
```

Los IDs autogenerados por SIH se exportan vacíos en el estado actual del código.

## 9. Metadata de exportación

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
```

Para errores incluye:

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

## 10. Relación con otros documentos

- Configuración SIH: `docs/SIH_CONFIGURATION.md`
- Matching de instrumentos: `docs/SIH_MATCHING.md`
- Solución de problemas: `docs/SIH_TROUBLESHOOTING.md`

## 11. Limitaciones actuales documentadas

Según el estado actual del código:

- el modo interactivo está aceptado por CLI, pero no implementa un menú completo;
- `quality_input_dir` existe en YAML, pero la integración con quality metrics no está usada todavía en la construcción de filas;
- `validation.py` es un placeholder para validaciones futuras;
- el matching de fechas/hora tolera algunos formatos en normalized, pero conviene estandarizar a `YYYYMMDD` y `HHMMSS`;
- los CSV de lookups deben existir en las rutas configuradas para que la exportación funcione.
