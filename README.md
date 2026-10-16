# Aforix

Aforix es una biblioteca y CLI en Python para procesar datos de aforos hidráulicos provenientes de instrumentos como FlowTracker, Molinete, Nivus y SonTek M9.

El objetivo es transformar archivos originales de campo en datasets consistentes, trazables, normalizados y listos para validación, exportación y análisis.

## Instrumentos contemplados

- FlowTracker
- Molinete
- Nivus
- SonTek M9: ingesta MAT, normalización y exportación SIH. Ver [alcance y aceptación](docs/M9_ACCEPTANCE.md) antes de la entrega a producción.

## Quickstart

Aforix requiere **Python 3.10 o superior**. Instale desde la raíz del repositorio para uso normal:

```bash
python -m pip install -e .
```

Para desarrollo, tests y validaciones de release:

```bash
python -m pip install -e ".[dev]"
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

Para ejecutar flujos reproducibles desde YAML, revisar la guía batch en `docs/BATCH_GUIDE.md`, los ejemplos en `configs/batches/examples/` y la guía de launchers en `docs/LAUNCHERS_GUIDE.md`.

Antes de liberar o usar Aforix en producción, revisar la checklist GO/NO-GO en `docs/RELEASE_CHECKLIST.md`.

## Salidas principales

- `runs/`: ejecuciones trazables del pipeline.
- `runs/batch/`: ejecuciones batch con `manifest.json` y reportes operativos.
- `database/raw_canonical/`: datos estructurados por instrumento consolidados por `build-groups`.
- `database/raw_canonical/_manifests/`: manifiestos de consolidación generados por `build-groups` cuando está habilitado.
- `database/normalized/`: datos normalizados bajo esquema común.
- `database/validation/`: reportes de validación.
- `outputs/`: exportaciones para usuario.

Estas carpetas son locales o generadas por el pipeline y no deberían versionarse en Git.

La estructura base de carpetas locales se conserva en el repositorio mediante archivos `.gitkeep`, de modo que un usuario que clone Aforix ya encontrará las carpetas necesarias (`data/raw/FT`, `data/raw/ML`, `data/raw/NV`, `database`, `outputs` y `runs`). Los datos reales, bases procesadas y outputs siguen ignorados por Git y no deben subirse al repositorio.

## Ruta de lectura recomendada

1. **Instalación y primera ejecución:** esta página y el Quickstart.
2. **Qué funciones están disponibles:** `docs/FUNCTIONALITIES.md`.
3. **Flujo de procesamiento:** `docs/02_pipeline.md`.
4. **Comandos y opciones:** `docs/03_cli.md`.
5. **Configuración del proyecto:** `docs/CONFIGURATION_GUIDE.md`.
6. **Ejecución reproducible:** `docs/BATCH_GUIDE.md` y `docs/LAUNCHERS_GUIDE.md`.
7. **Modos interactivos:** `docs/INTERACTIVE_USAGE.md`.
8. **Análisis y exportaciones específicas:** las guías listadas abajo.
9. **Antes de entregar o usar en producción:** `docs/RELEASE_CHECKLIST.md`.

## Documentación

- Funcionalidades y alcance: `docs/FUNCTIONALITIES.md`
- Pipeline de procesamiento: `docs/02_pipeline.md`
- Referencia CLI: `docs/03_cli.md`
- Checklist de liberación a producción: `docs/RELEASE_CHECKLIST.md`
- Guía batch: `docs/BATCH_GUIDE.md`
- Ejemplos batch: `configs/batches/examples/README.md`
- Guía de launchers Windows/Linux: `docs/LAUNCHERS_GUIDE.md`
- Uso interactivo y estrategia de launchers: `docs/INTERACTIVE_USAGE.md`
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

Funciones disponibles actualmente:

- ingesta de archivos de FlowTracker, Molinete y Nivus;
- extracción configurable de metadata mediante `metadata_policy`;
- consolidación en `database/raw_canonical` y normalización con reglas YAML;
- auditoría técnica y validación de datos normalizados;
- exportación de tablas y Excel, además de exportación configurable a SIH;
- análisis de correlación, métricas de calidad, caudal–altura y perfiles de sección;
- conversión de datos externos de modelo, DINAGUA y niveles manuales;
- ejecución batch desde YAML, con validación, planificación, simulación y manifiestos;
- modos interactivos para exportar tablas, exportar a SIH, analizar caudal–altura y generar perfiles de sección.

La descripción funcional y los comandos están en `docs/FUNCTIONALITIES.md`; la referencia completa de opciones está en `docs/03_cli.md`.

Pendiente de implementación y fuera del alcance actual de producción:

- ingesta M9 / ADCP;
- análisis estadístico (`aforix analyze statistics`), que actualmente termina con un mensaje explícito de función no implementada.

## Autor

Rafael Rosa
