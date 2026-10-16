# CLI de Aforix

Este documento describe los comandos disponibles en la interfaz de línea de comandos de Aforix y el flujo operativo recomendado.

La CLI se ejecuta con:

```bash
aforix <command> [options]
```

La opción común más usada es:

```bash
-c, --config PATH
```

Ejemplo:

```bash
aforix config-check -c configs/examples/main.yaml
```

## Relación con el pipeline

```text
raw -> ingest -> runs/.../raw_canonical -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> audit/validate/export/analysis
```

Comandos principales por etapa:

| Etapa | Comando |
| --- | --- |
| Revisar configuración | `aforix config-check` |
| Ingesta | `aforix ingest <instrument>` |
| Construcción canónica | `aforix build-groups` |
| Filtro de grupos | `aforix filter-groups` |
| Normalización | `aforix normalize run` |
| Auditoría técnica | `python scripts/audit_pipeline_outputs.py` |
| Validación | `aforix validate run` |
| Exportación | `aforix export ...` |
| Análisis | `aforix analyze ...` |
| Conversión de fuentes externas | `aforix external ...` |
| Flujos YAML reproducibles | `aforix batch ...` |

## Ayuda general

```bash
aforix --help
```

Ayuda por subcomando:

```bash
aforix ingest --help
aforix normalize --help
aforix export --help
aforix analyze --help
```

## config-check

Valida que el archivo de configuración pueda cargarse correctamente.

```bash
aforix config-check -c configs/examples/main.yaml
```

Uso recomendado: ejecutar este comando antes del resto del pipeline.

## ingest

Lee archivos raw y genera salidas estructuradas por instrumento dentro de `runs/`.

La metadata principal de trazabilidad se extrae según `metadata_policy` en `configs/examples/main.yaml`.

Campos principales:

```text
station_id
station_name
measurement_date
measurement_time
```

### FlowTracker

```bash
aforix ingest flowtracker -c configs/examples/main.yaml
```

### Molinete

```bash
aforix ingest molinete -c configs/examples/main.yaml
```

### Nivus

```bash
aforix ingest nivus -c configs/examples/main.yaml
```

### M9 / ADCP

La ingesta M9 procesa exportaciones MAT de RiverSurveyor Live. Alcance validado y pendientes de entrega: [aceptación M9](M9_ACCEPTANCE.md).

```bash
aforix ingest m9 -c configs/examples/main.yaml
```

La ingesta lee los archivos `.mat` exportados por RiverSurveyor Live desde `data/raw/M9/` y produce `Summary` y `Points`. El archivo nativo `.rivr` se conserva como original, pero no se interpreta directamente. El M9 está incorporado a la normalización y a la exportación SIH; el catálogo local usa el código de instrumento `503`.

Flujo local completo, después de copiar los `.mat` a `data/raw/M9/`:

```bash
aforix ingest m9 -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
```

La ingesta escribe una ejecución nueva bajo `runs/`; `build-groups` actualiza `database/raw_canonical/` y la normalización publica las tablas en `database/normalized/`.

El `hydraulic_radius_m` del M9 se obtiene como `area_total_m2 / wetted_perimeter_m`. El perímetro se calcula sobre el perfil de profundidades de `Points`; cuando el MAT informa distancia a las márgenes, se agrega un segmento lineal desde profundidad cero hasta la primera/última muestra. Ese supuesto queda identificado por `hydraulic_radius_method` en `Summary`.

Para revisión local, Aforix calcula un **IVE adaptado al M9** sobre las muestras de perfil de un segundo: proyecta `Mean_Vel` a la normal de la transecta y aplica la integración mid-section, los residuos de interpolación y los componentes sistemáticos/ancho del método IVE de Aforix (`u_s=1 %`, `u_b=0,5 %`, `s_d,min=0,01 m`; usa `s_v,IVE` sin piso instrumental). El resultado se etiqueta `IVE_ADAPTADO_M9` y no se presenta como equivalente a QRev. La exportación SIH incluye `incertidumbre_IVE` (porcentaje), `error_IVE` (m³/s, usando Q mid-section) y `calidad_IVE`. El carácter análogo debe tenerse en cuenta al interpretar estos resultados.

## build-groups

Consolida salidas de ingesta y construye la base `database/raw_canonical/`.

```bash
aforix build-groups -c configs/examples/main.yaml
```

Este comando se ejecuta después de la ingesta y antes de la normalización.

Su comportamiento depende de la sección `build_groups` del YAML, incluyendo:

```text
use_latest_run_only
include_runs
exclude_runs
deduplicate
deduplicate_by
manifest
```

Cuando `manifest` está habilitado, se generan manifiestos en:

```text
database/raw_canonical/_manifests/
```

## filter-groups

Aplica filtros sobre los datasets agrupados.

```bash
aforix filter-groups -c configs/examples/main.yaml
```

Este paso puede usarse cuando la configuración define criterios para seleccionar o depurar grupos antes de continuar el pipeline.

## normalize run

Normaliza la base `database/raw_canonical/` usando el registry de normalización.

```bash
aforix normalize run -c configs/examples/main.yaml
```

Salida esperada:

```text
database/normalized/
```

Este es el comando que genera los datasets comparables entre instrumentos.

El comportamiento de escritura se controla con:

```yaml
normalize:
  write_policy: overwrite
```

Valores soportados:

| Valor | Comportamiento |
| --- | --- |
| `overwrite` | sobrescribe outputs existentes e informa la acción |
| `fail_if_exists` | detiene la normalización si el output ya existe |

## audit pipeline outputs

Aforix incluye un script de auditoría técnica para revisar los outputs principales del pipeline:

```bash
python scripts/audit_pipeline_outputs.py
```

En Windows CMD:

```bat
python scripts\audit_pipeline_outputs.py
```

El script revisa:

- `database/raw_canonical`;
- `database/normalized`;
- columnas esperadas;
- duplicados;
- consistencia hidráulica entre `Summary` y `Points`;
- consistencia de unidades m3/s ↔ L/s;
- rangos básicos.

Los caudales negativos se tratan como información, no necesariamente como error. Nivus `Gates` puede quedar como `not_checked` hasta definir una clave única confiable.

Este script no reemplaza `aforix validate run`. El audit es una revisión técnica amplia; `validate` es la validación formal configurada en YAML.

## validate run

Ejecuta validaciones sobre los datasets normalizados.

```bash
aforix validate run -c configs/examples/main.yaml
```

Salida esperada:

```text
database/validation/
```

Ejemplos de chequeos:

- columnas requeridas;
- duplicados;
- completitud;
- rangos válidos;
- consistencia hidráulica.

## export

Agrupa comandos de exportación.

### export tables

Exporta tablas desde `database/normalized/`.

Modo interactivo:

```bash
aforix export tables -c configs/examples/main.yaml --interactive
```

Modo no interactivo: revisar las opciones disponibles con:

```bash
aforix export tables --help
```

### export excel

Exporta resultados a Excel usando la configuración del proyecto.

```bash
aforix export excel -c configs/examples/main.yaml
```

### export sih

Exporta mediciones al formato SIH.

```bash
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml
```

Modo interactivo SIH:

```bash
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml --interactive
```

Más detalles:

```text
docs/SIH_EXPORT.md
docs/SIH_CONFIGURATION.md
docs/SIH_MATCHING.md
docs/SIH_TROUBLESHOOTING.md
```

## analyze

Agrupa comandos de análisis.

### analyze statistics

Este comando está reservado para desarrollo futuro. La funcionalidad estadística todavía no está implementada; al invocarlo, Aforix muestra un mensaje y termina con código de error, sin crear una corrida.

```bash
aforix analyze statistics -c configs/examples/main.yaml
```

### analyze correlation

```bash
aforix analyze correlation run -c configs/examples/main.yaml
```

### analyze quality

```bash
aforix analyze quality run -c configs/examples/main.yaml
```

### analyze stage-discharge

Ejecución con parámetros del YAML:

```bash
aforix analyze stage-discharge run -c configs/examples/main.yaml
```

Modo interactivo:

```bash
aforix analyze stage-discharge interactive -c configs/examples/main.yaml
```

### analyze section-profiles

Ejecución con parámetros del YAML:

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml
```

Modo interactivo:

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml --interactive
```

Los tipos de gráfico admitidos son `scatter` y `bar`.

La capa de análisis debe trabajar preferentemente sobre datos normalizados o fuentes externas normalizadas.

## external

Convierte datos externos a formatos normalizados que pueden usar los análisis.

```bash
aforix external --help
aforix external convert-model -c configs/examples/main.yaml
aforix external convert-dinagua -c configs/examples/main.yaml
aforix external convert-manual-stage -c configs/examples/main.yaml
```

Las rutas de entrada y salida se configuran en `external_sources` dentro del YAML principal. La guía de configuración y las guías de análisis describen los formatos esperados.

## batch

Los flujos batch permiten validar, planificar y ejecutar recetas YAML con manifiestos de corrida.

```bash
aforix batch --help
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
```

Para la sintaxis YAML, los ejemplos y el flujo de ejecución, consulta `docs/BATCH_GUIDE.md`.

## consolidate

Agrupa comandos de consolidación específicos.

### consolidate flowtracker

Consolida salidas de una ejecución de ingesta FlowTracker en una base estable.

```bash
aforix consolidate flowtracker --run-dir runs/ingest_flowtracker/<timestamp> --database-root database
```

Este comando es más específico que `build-groups` y puede ser útil para flujos heredados o tareas puntuales de FlowTracker.

## Flujo recomendado

Ejemplo completo con los instrumentos actualmente considerados estables:

```bash
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts/audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
aforix export tables -c configs/examples/main.yaml --interactive
```

Windows CMD:

```bat
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts\audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
aforix export tables -c configs/examples/main.yaml --interactive
```

Para múltiples instrumentos, ejecutar primero las ingestas necesarias y luego continuar con `build-groups`, `normalize run`, auditoría y `validate run`.

## Notas

- Los comandos deben ejecutarse desde un entorno donde el paquete esté instalado, por ejemplo con `python -m pip install -e .`.
- Para desarrollo y testing, usar `python -m pip install -e ".[dev]"`.
- Revisar `docs/RELEASE_CHECKLIST.md` antes de una liberación o uso en producción.
- La configuración se centraliza en un archivo YAML.
- Las salidas locales se escriben principalmente en `runs/`, `database/` y `outputs/`.
- No modificar manualmente los archivos normalizados salvo para inspección o depuración controlada.
