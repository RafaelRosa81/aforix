# Pipeline de procesamiento

Aforix transforma datos de aforos mediante un flujo por etapas. Este documento define la referencia principal del pipeline.

## Flujo general

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

## 1. raw

Archivos originales generados por cada instrumento.

Ejemplos:

- FlowTracker
- Molinete
- Nivus
- M9 / ADCP, previsto para una etapa posterior

Aforix no modifica directamente estos archivos.

## 2. ingest

Lee archivos raw y genera salidas estructuradas por instrumento.

Ejemplo:

```bash
aforix ingest flowtracker -c configs/examples/main.yaml
```

La salida se guarda en `runs/` para mantener trazabilidad de cada ejecución.

## 3. runs

Cada ejecución queda registrada en una carpeta independiente. Esto permite revisar resultados intermedios, auditar procesos y repetir etapas si es necesario.

## 4. build-groups

Consolida salidas de ingesta y construye la base canónica local.

```bash
aforix build-groups -c configs/examples/main.yaml
```

Salida principal:

```text
database/raw_canonical/
```

## 5. database/raw_canonical

Contiene datos estructurados pero todavía cercanos a cada instrumento. Es la entrada de la normalización.

## 6. normalize

Convierte datos canónicos en tablas comparables entre instrumentos.

```bash
aforix normalize run -c configs/examples/main.yaml
```

Salida principal:

```text
database/normalized/
```

## 7. database/normalized

Contiene datasets bajo un esquema común. Es la base recomendada para validación, exportación y análisis.

## 8. validate

Aplica controles de consistencia sobre los datos normalizados.

```bash
aforix validate run -c configs/examples/main.yaml
```

Salida principal:

```text
database/validation/
```

## 9. export

Genera salidas orientadas a usuarios finales.

```bash
aforix export tables -c configs/examples/main.yaml --interactive
```

## 10. analysis

Incluye procesos hidrológicos o estadísticos posteriores. Esta capa debe trabajar sobre `database/normalized/`.

## Principios

- Separar responsabilidades por etapa.
- Mantener trazabilidad desde archivos originales hasta salidas finales.
- Persistir resultados intermedios.
- Usar configuración YAML para reproducibilidad.
- Incorporar nuevos instrumentos mediante adapters y reglas de normalización.
