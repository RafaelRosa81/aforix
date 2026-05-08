# Arquitectura de Aforix

Este documento describe la arquitectura técnica de Aforix. Está orientado a desarrollo y mantenimiento del proyecto.

Para usuarios finales, comenzar por el README y la guía de configuración. Para entender el flujo funcional del sistema, revisar `docs/02_pipeline.md`.

## Objetivo arquitectónico

Aforix busca separar claramente:

- lectura de archivos originales por instrumento;
- persistencia de ejecuciones intermedias;
- construcción de una base canónica;
- normalización a esquemas comunes;
- validación de consistencia;
- exportación y análisis.

La regla principal es que las funciones de análisis y exportación no dependan directamente de formatos raw de instrumentos.

## Pipeline general

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

La definición canónica del pipeline está en `docs/02_pipeline.md`.

## Estructura principal del paquete

```text
src/aforix/
├── analysis/
├── cli/
├── config/
├── database/
├── export/
├── filters/
├── groups/
├── ingest/
├── normalize/
├── runs/
└── validation/
```

## Módulos

### cli

Define la interfaz de línea de comandos usando Typer.

Responsabilidades:

- registrar comandos principales;
- validar configuración antes de ejecutar módulos;
- conectar comandos de usuario con funciones internas.

Comandos relevantes:

- `aforix config-check`
- `aforix ingest <instrument>`
- `aforix build-groups`
- `aforix filter-groups`
- `aforix normalize run`
- `aforix validate run`
- `aforix export ...`
- `aforix analyze ...`

La referencia de CLI está en `docs/03_cli.md`.

### config

Carga y valida archivos YAML de configuración.

Responsabilidades:

- leer `main.yaml`;
- validar secciones obligatorias;
- exponer rutas e instrucciones al resto del pipeline;
- evitar que los módulos operen con configuración incompleta.

### ingest

Contiene adaptadores específicos por instrumento.

Responsabilidades:

- leer archivos raw;
- extraer metadatos de medición;
- generar tablas iniciales estructuradas;
- preservar trazabilidad hacia archivo fuente y ejecución.

Instrumentos actuales:

- FlowTracker;
- Molinete;
- Nivus;
- M9, previsto o experimental según el estado del adaptador.

Principio de diseño: las particularidades de cada instrumento deben quedar dentro de `ingest/`, no propagarse a análisis o exportación.

### runs

Gestiona carpetas de ejecución.

Responsabilidades:

- crear directorios por etapa y timestamp;
- permitir trazabilidad;
- facilitar auditoría y depuración;
- preservar salidas intermedias.

Ejemplo conceptual:

```text
runs/ingest_flowtracker/<timestamp>/outputs/
```

### groups

Construye datasets agrupados o bases canónicas a partir de salidas de ingesta.

Responsabilidades:

- reunir resultados de uno o más runs;
- ordenar outputs por instrumento y tabla;
- generar `database/raw_canonical/`.

### database

Contiene utilidades para consolidar información en una base local estable.

Responsabilidades:

- mover o consolidar outputs intermedios hacia `database/`;
- mantener estructuras persistentes para etapas posteriores;
- evitar que análisis dependa directamente de `runs/`.

### normalize

Normaliza datasets canónicos usando reglas declarativas.

Responsabilidades:

- leer `database/raw_canonical/`;
- aplicar specs YAML desde `configs/normalization/`;
- mapear columnas de cada instrumento a columnas comunes;
- crear tablas normalizadas en `database/normalized/`.

Principio de diseño: agregar una columna o ajustar el origen de un campo debería resolverse preferentemente en el registry YAML, no hardcodeando reglas dentro del código.

### validation

Ejecuta chequeos sobre datasets normalizados.

Responsabilidades:

- verificar columnas requeridas;
- detectar duplicados;
- revisar completitud;
- validar rangos;
- evaluar consistencia hidráulica.

Las validaciones deben trabajar sobre `database/normalized/`, no directamente sobre archivos raw.

### export

Genera salidas para usuarios finales.

Responsabilidades:

- leer datos normalizados;
- permitir selección de tablas, instrumentos, puntos, fechas y parámetros;
- exportar a formatos como Excel o CSV.

Submódulos relevantes:

- `export/sih`: exportación configurable SIH usando normalized, raw canonical y lookups (`docs/SIH_EXPORT.md`).

### analysis

Contiene análisis hidrológicos o estadísticos posteriores.

Responsabilidades:

- calcular métricas;
- construir series o comparaciones;
- operar sobre datasets normalizados.

Submódulos relevantes:

- `analysis/correlation`: correlación entre aforos, modelo y estaciones DINAGUA (`docs/CORRELATION_GUIDE.md`).
- `analysis/quality`: métricas de calidad de medición (`docs/QUALITY_METRICS_GUIDE.md`).
- `analysis/stage_discharge`: análisis caudal-altura (`docs/STAGE_DISCHARGE_ANALYSIS.md`).
- `analysis/section_profiles`: perfiles de sección (`docs/SECTION_PROFILES_ANALYSIS.md`).

Este módulo debe mantenerse desacoplado de formatos propios de instrumentos.

### filters

Contiene filtros sobre grupos o datasets intermedios.

Responsabilidades:

- aplicar criterios definidos en configuración;
- preparar subconjuntos antes de normalización o análisis.

## Capas de datos

### raw

Archivos originales del usuario. No deberían modificarse.

### runs

Salidas trazables por ejecución. Son útiles para auditoría y depuración.

### database/raw_canonical

Datos estructurados y consolidados, todavía cercanos a cada instrumento.

### database/normalized

Datos bajo esquema común. Es la capa recomendada para validación, exportación y análisis.

### database/validation

Reportes de validación.

### outputs

Salidas finales orientadas a usuarios.

## Principios de diseño

### Separación por responsabilidad

Cada módulo debe tener una función clara. La ingesta no debería realizar análisis, y el análisis no debería conocer formatos raw.

### Trazabilidad

Los datos procesados deben conservar referencia a su archivo fuente, instrumento y ejecución.

### Configuración declarativa

La configuración YAML debe controlar rutas, instrumentos activos, reglas de normalización, validaciones y exportaciones.

### Extensibilidad por instrumento

Para agregar un instrumento nuevo se debe priorizar:

1. crear o completar el adaptador en `ingest/`;
2. generar salidas raw canonical consistentes;
3. definir specs en `configs/normalization/`;
4. validar `Summary` y `Points` normalizados;
5. documentar requisitos de configuración.

### Análisis sobre datos normalizados

Los módulos de análisis deben consumir `database/normalized/`. Esto evita duplicar lógica específica de instrumentos.

## Flujo recomendado para nuevos desarrollos

1. Crear una rama desde `main`.
2. Implementar o ajustar un módulo pequeño.
3. Actualizar documentación relacionada.
4. Ejecutar el pipeline mínimo.
5. Abrir Pull Request.

## Estado actual

Componentes disponibles:

- CLI principal;
- ingesta FlowTracker;
- ingesta Molinete;
- ingesta Nivus;
- construcción de `database/raw_canonical/`;
- normalización mediante registry YAML;
- validación de datasets normalizados;
- exportación de tablas;
- exportación SIH configurable.

Componentes pendientes o en evolución:

- ingesta M9 completa;
- análisis hidrológicos avanzados;
- consolidación de modelo de datos documentado;
- pruebas automáticas más amplias.
