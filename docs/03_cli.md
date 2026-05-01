# CLI de Aforix

Este documento describe los comandos disponibles en la interfaz de línea de comandos de Aforix.

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
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

Comandos principales por etapa:

| Etapa | Comando |
| --- | --- |
| Revisar configuración | `aforix config-check` |
| Ingesta | `aforix ingest <instrument>` |
| Construcción canónica | `aforix build-groups` |
| Filtro de grupos | `aforix filter-groups` |
| Normalización | `aforix normalize run` |
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
```

## config-check

Valida que el archivo de configuración pueda cargarse correctamente.

```bash
aforix config-check -c configs/examples/main.yaml
```

Uso recomendado: ejecutar este comando antes del resto del pipeline.

## ingest

Lee archivos raw y genera salidas estructuradas por instrumento dentro de `runs/`.

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

## analyze

Agrupa comandos de análisis.

### analyze statistics

Ejecuta análisis estadísticos definidos para el proyecto.

```bash
aforix analyze statistics -c configs/examples/main.yaml
```

La capa de análisis debe trabajar preferentemente sobre datos normalizados.

## consolidate

Agrupa comandos de consolidación específicos.

### consolidate flowtracker

Consolida salidas de una ejecución de ingesta FlowTracker en una base estable.

```bash
aforix consolidate flowtracker --run-dir runs/ingest_flowtracker/<timestamp> --database-root database
```

Este comando es más específico que `build-groups` y puede ser útil para flujos heredados o tareas puntuales de FlowTracker.

## Flujo recomendado

Ejemplo mínimo con FlowTracker:

```bash
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
aforix validate run -c configs/examples/main.yaml
aforix export tables -c configs/examples/main.yaml --interactive
```

Para múltiples instrumentos, ejecutar primero las ingestas necesarias y luego continuar con `build-groups`, `normalize run` y `validate run`.

## Notas

- Los comandos deben ejecutarse desde un entorno donde el paquete esté instalado, por ejemplo con `pip install -e .`.
- La configuración se centraliza en un archivo YAML.
- Las salidas locales se escriben principalmente en `runs/`, `database/` y `outputs/`.
- No modificar manualmente los archivos normalizados salvo para inspección o depuración controlada.
