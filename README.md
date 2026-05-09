# Aforix

Aforix es una biblioteca y CLI en Python para procesar datos de aforos hidráulicos provenientes de instrumentos como FlowTracker, Molinete y Nivus.

El objetivo es transformar archivos originales de campo en datasets consistentes, trazables, normalizados y listos para validación, exportación y análisis.

## Instrumentos contemplados

- FlowTracker
- Molinete
- Nivus
- M9 / ADCP, previsto para una etapa posterior

## Quickstart

Instalar desde la raíz del repositorio:

```bash
pip install -e .
```

Verificar el CLI:

```bash
aforix --help
```

Ejecutar un flujo básico:

```bash
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts/audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
```

En Windows CMD:

```bat
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts\audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
```

## Pipeline

```text
raw -> ingest -> runs/.../raw_canonical -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> audit/validate/export/analysis
```

La explicación completa del flujo está en `docs/02_pipeline.md`.

Para ejecutar flujos reproducibles desde YAML, revisar la guía batch en `docs/BATCH_GUIDE.md` y los ejemplos en `configs/batches/examples/`.

## Salidas principales

- `runs/`: ejecuciones trazables del pipeline.
- `runs/batch/`: ejecuciones batch con `manifest.json` y reportes operativos.
- `database/raw_canonical/`: datos estructurados por instrumento consolidados por `build-groups`.
- `database/raw_canonical/_manifests/`: manifiestos de consolidación generados por `build-groups` cuando está habilitado.
- `database/normalized/`: datos normalizados bajo esquema común.
- `database/validation/`: reportes de validación.
- `outputs/`: exportaciones para usuario.

Estas carpetas son locales o generadas por el pipeline y no deberían versionarse en Git.

## Documentación

- Pipeline de procesamiento: `docs/02_pipeline.md`
- Referencia CLI: `docs/03_cli.md`
- Guía batch: `docs/BATCH_GUIDE.md`
- Ejemplos batch: `configs/batches/examples/README.md`
- Guía de configuración: `docs/CONFIGURATION_GUIDE.md`
- Guía de análisis de correlación: `docs/CORRELATION_GUIDE.md`
- Guía de métricas de calidad: `docs/QUALITY_METRICS_GUIDE.md`
- Guía de análisis caudal–altura: `docs/STAGE_DISCHARGE_ANALYSIS.md`
- Guía de perfiles de sección: `docs/SECTION_PROFILES_ANALYSIS.md`
- Guía de exportación SIH: `docs/SIH_EXPORT.md`
- Configuración SIH: `docs/SIH_CONFIGURATION.md`
- Matching SIH: `docs/SIH_MATCHING.md`
- Troubleshooting SIH: `docs/SIH_TROUBLESHOOTING.md`
- Modelo de datos: `docs/06_data_model.md`
- Arquitectura del proyecto: `docs/ARCHITECTURE.md`
- Reglas para agentes y desarrollo asistido: `AGENTS.md`

## Estado del proyecto

Aforix está en desarrollo activo. El trabajo se organiza mediante ramas y Pull Requests.

Componentes disponibles actualmente:

- ingesta de FlowTracker, Molinete y Nivus;
- extracción configurable de metadata mediante `metadata_policy`;
- construcción configurable de `database/raw_canonical`;
- normalización mediante registry YAML y política de escritura;
- auditoría técnica de outputs del pipeline;
- validación de datasets normalizados;
- infraestructura batch con YAML, `CommandResult`, `manifest.json` y métricas operativas;
- exportación de tablas;
- exportación SIH configurable.

## Autor

Rafael Rosa
