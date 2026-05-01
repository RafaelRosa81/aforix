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
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
aforix validate run -c configs/examples/main.yaml
```

## Pipeline

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

La explicación completa del flujo está en `docs/02_pipeline.md`.

## Salidas principales

- `runs/`: ejecuciones trazables del pipeline.
- `database/raw_canonical/`: datos estructurados por instrumento.
- `database/normalized/`: datos normalizados bajo esquema común.
- `database/validation/`: reportes de validación.
- `outputs/`: exportaciones para usuario.

Estas carpetas son locales o generadas por el pipeline y no deberían versionarse en Git.

## Documentación

- Pipeline de procesamiento: `docs/02_pipeline.md`
- Referencia CLI: `docs/03_cli.md`
- Guía de configuración: `docs/CONFIGURATION_GUIDE.md`
- Modelo de datos: `docs/06_data_model.md`
- Arquitectura del proyecto: `docs/ARCHITECTURE.md`
- Reglas para agentes y desarrollo asistido: `AGENTS.md`

## Estado del proyecto

Aforix está en desarrollo activo. El trabajo se organiza mediante ramas y Pull Requests.

Componentes disponibles actualmente:

- ingesta de FlowTracker, Molinete y Nivus;
- construcción de `database/raw_canonical`;
- normalización mediante registry YAML;
- validación de datasets normalizados;
- exportación de tablas.

## Autor

Rafael Rosa
