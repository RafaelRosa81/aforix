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

### M9

```bash
aforix ingest m9 -c configs/examples/main.yaml
```

M9 está previsto para una etapa posterior o puede considerarse experimental según el estado del proyecto.

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

Ejecuta análisis estadísticos definidos para el proyecto.

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

```bash
aforix analyze stage-discharge run -c configs/examples/main.yaml
```

### analyze section-profiles

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml
```

La capa de análisis debe trabajar preferentemente sobre datos normalizados o fuentes externas normalizadas.

## consolidate

Agrupa comandos de consolidación específicos.

### consolidate flowtracker

Consolida salidas de una ejecución de ingesta FlowTracker en una base estable.

```bash
aforix consolidate flowtracker --run-dir runs/ingest_flowtracker/<timestamp> --database-root database
```

Este comando es más específico que `build-groups` y puede ser útil para flujos heredados o tareas puntuales de FlowTracker.

## Flujo recomendado

Ejemplo completo con los instrumentos actuales:

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

- Los comandos deben ejecutarse desde un entorno donde el paquete esté instalado, por ejemplo con `pip install -e .`.
- La configuración se centraliza en un archivo YAML.
- Las salidas locales se escriben principalmente en `runs/`, `database/` y `outputs/`.
- No modificar manualmente los archivos normalizados salvo para inspección o depuración controlada.
