# Funcionalidades de Aforix

Aforix convierte datos de aforos de campo en resultados trazables, normalizados y listos para validación, exportación y análisis. Esta guía resume qué está implementado, cómo se ejecuta y qué sigue pendiente.

## Instrumentos dentro del flujo de producción

| Instrumento | Comando de ingesta | Entrada configurada |
| --- | --- | --- |
| FlowTracker | `aforix ingest flowtracker -c configs/examples/main.yaml` | `data/raw/FT` |
| Molinete | `aforix ingest molinete -c configs/examples/main.yaml` | `data/raw/ML` |
| Nivus | `aforix ingest nivus -c configs/examples/main.yaml` | `data/raw/NV` |
| SonTek M9 | `aforix ingest m9 -c configs/examples/main.yaml` | `data/raw/M9` (`.mat`) |

Las reglas de extracción de estación, nombre, fecha y hora se definen por instrumento en `configs/examples/main.yaml`. Las ingestas escriben corridas trazables bajo `runs/`. M9 genera `Summary` y `Points` por MAT; las transectas se conservan separadas y no se promedian. Consulte [la guía M9](M9_PROCESSING_GUIDE.md).

## Flujo de preparación y control de datos

Después de la ingesta, los comandos principales son:

```bash
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts/audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
```

- **build-groups** consolida las salidas de ingesta en `database/raw_canonical/`.
- **normalize run** aplica reglas YAML por instrumento y genera tablas comparables en `database/normalized/`.
- **audit_pipeline_outputs.py** revisa estructura, duplicados y consistencia hidráulica.
- **validate run** aplica los controles configurados y escribe reportes en `database/validation/`.

## Exportaciones

- **Tablas:** exporta datos normalizados a XLSX o CSV, con filtros de tabla, instrumento, puntos y fechas. Puede ejecutarse de forma guiada:
  `aforix export tables -c configs/examples/main.yaml --interactive`.
- **Excel:** genera salidas Excel según la configuración del proyecto:
  `aforix export excel -c configs/examples/main.yaml`.
- **SIH:** convierte mediciones seleccionadas al formato de exportación configurado:
  `aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml`.
  Tiene también un modo interactivo. Los detalles están en `docs/SIH_EXPORT.md`.

## Análisis

| Función | Comando |
| --- | --- |
| Correlación | `aforix analyze correlation run -c configs/examples/main.yaml` |
| Métricas de calidad | `aforix analyze quality run -c configs/examples/main.yaml` |
| Caudal–altura | `aforix analyze stage-discharge run -c configs/examples/main.yaml` |
| Perfiles de sección | `aforix analyze section-profiles run -c configs/examples/main.yaml` |

Caudal–altura y perfiles de sección también permiten selección interactiva. Las guías específicas están en `docs/CORRELATION_GUIDE.md`, `docs/QUALITY_METRICS_GUIDE.md`, `docs/STAGE_DISCHARGE_ANALYSIS.md` y `docs/SECTION_PROFILES_ANALYSIS.md`.

## Fuentes externas

Aforix incluye conversores configurables para datos de modelo, estaciones DINAGUA y niveles manuales:

```bash
aforix external convert-model -c configs/examples/main.yaml
aforix external convert-dinagua -c configs/examples/main.yaml
aforix external convert-manual-stage -c configs/examples/main.yaml
```

Las rutas de entrada y salida se definen bajo `external_sources` en el YAML principal.

## Ejecución reproducible

El subsistema batch permite validar, planificar y ejecutar recetas YAML. Para revisar los comandos y opciones:

```bash
aforix batch --help
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
```

Los launchers de Windows y Linux se documentan en `docs/LAUNCHERS_GUIDE.md`.

## Modos interactivos disponibles

1. Exportación de tablas.
2. Exportación al SIH.
3. Análisis caudal–altura.
4. Perfiles de sección.

Los comandos concretos y lo que pregunta cada flujo están en `docs/INTERACTIVE_USAGE.md`. El modo interactivo general todavía no está implementado. Los flujos interactivos no se ejecutan dentro de batch.

## Funciones pendientes

- **Estadística:** `aforix analyze statistics` está reservado y termina con un mensaje de función no implementada.

No deben tratarse como funcionalidades de producción hasta que se implementen y validen.

## Referencias

- Primer uso e instalación: `README.md`.
- Flujo detallado: `docs/02_pipeline.md`.
- Comandos y opciones: `docs/03_cli.md`.
- Configuración: `docs/CONFIGURATION_GUIDE.md`.
- Uso interactivo: `docs/INTERACTIVE_USAGE.md`.
- Lista de verificación de liberación: `docs/RELEASE_CHECKLIST.md`.
