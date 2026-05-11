# Checklist de liberación a producción de Aforix

Esta checklist define las verificaciones mínimas GO/NO-GO antes de usar Aforix en producción.

Alcance de esta liberación:

- FlowTracker, Molinete y Nivus están dentro del alcance.
- M9 queda fuera del alcance de esta liberación de producción y se abordará en un ciclo posterior de estabilización.
- Las verificaciones que requieren datos hidrológicos locales no versionados son verificaciones manuales y no deben tratarse como trabajos obligatorios de CI.

## 1. Instalación limpia

Objetivo: verificar que Aforix pueda instalarse desde un entorno limpio.

Criterios GO:

- La instalación editable finaliza sin errores de dependencias.
- Las dependencias de runtime y desarrollo se instalan desde `pyproject.toml`.

Windows CMD:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Resultado esperado:

- La instalación finaliza correctamente.
- No aparecen errores `ModuleNotFoundError` ni errores de resolución de dependencias.

NO-GO si:

- La instalación falla.
- `.[dev]` no es reconocido.
- Faltan dependencias runtime requeridas.

## 2. Imports runtime críticos

Objetivo: verificar que las dependencias principales de análisis y batch estén disponibles después de la instalación.

Windows CMD:

```bat
python -c "import sklearn, scipy, matplotlib, psutil; print('OK')"
```

Resultado esperado:

```text
OK
```

NO-GO si:

- Cualquier import falla.

## 3. Smoke test del CLI

Objetivo: verificar que el CLI y los subcomandos principales carguen correctamente.

Windows CMD:

```bat
aforix --help
aforix ingest --help
aforix export --help
aforix analyze --help
aforix normalize --help
aforix validate --help
aforix batch --help
aforix external --help
```

Resultado esperado:

- Se muestra la ayuda de Typer para cada comando.
- No hay errores de importación.
- No hay traceback inesperado.

NO-GO si:

- El CLI raíz no inicia.
- Algún subcomando de producción no carga.

## 4. Verificación de configuración

Objetivo: verificar que la configuración de ejemplo del proyecto sea estructuralmente válida.

Windows CMD:

```bat
aforix config-check -c configs/examples/main.yaml
```

Resultado esperado:

- La configuración carga correctamente.
- No hay errores de validación.

NO-GO si:

- El YAML no puede leerse.
- Faltan secciones requeridas.
- Falla la validación de configuración.

## 5. Suite de tests

Objetivo: verificar la línea base actual de regresión.

Windows CMD:

```bat
pytest -q
```

Resultado esperado:

- Todos los tests pasan.

NO-GO si:

- Algún test falla.
- Los tests no pueden colectarse.
- `aforix` no puede importarse desde los tests.

## 6. Verificación de compilación

Objetivo: verificar que los archivos Python en `src` y `scripts` compilen correctamente.

Windows CMD:

```bat
python -m compileall src scripts
```

Resultado esperado:

- No hay errores de sintaxis.

NO-GO si:

- Algún archivo fuente o script falla al compilar.

## 7. Smoke test de batch

Objetivo: verificar que la orquestación batch pueda validar, planificar y ejecutar un dry-run mínimo.

Windows CMD:

```bat
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch plan -b configs/batches/examples/check_only.yaml
aforix batch run -b configs/batches/examples/check_only.yaml --dry-run
```

Resultado esperado:

- La validación batch finaliza correctamente.
- El plan de ejecución se imprime.
- El dry-run finaliza sin ejecutar procesamiento de dominio.

NO-GO si:

- El YAML batch no puede cargarse.
- Falta un comando registrado.
- El dry-run falla.

## 8. Smoke test local del pipeline de producción

Objetivo: verificar el pipeline real con datos locales. Esta verificación depende de datos locales no versionados y no es adecuada para CI.

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
```

Resultado esperado:

- Cada etapa finaliza correctamente.
- Las salidas normalizadas se generan en `database/normalized`.
- Los reportes de auditoría y validación no muestran inconsistencias bloqueantes.

NO-GO si:

- Algún instrumento de producción dentro del alcance falla inesperadamente.
- Faltan salidas normalizadas o son inconsistentes.
- La validación reporta errores bloqueantes que afectan los resultados.

## 9. Smoke test de exportación SIH

Objetivo: verificar que los comandos y la configuración de exportación SIH carguen correctamente.

Windows CMD:

```bat
aforix export sih --help
aforix config-check -c configs/examples/main.yaml
```

Verificación manual con datos normalizados locales:

```bat
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml
```

Resultado esperado:

- La ayuda de SIH carga correctamente.
- La configuración SIH puede usarse cuando existen datos normalizados.
- Los archivos exportados siguen la estructura SIH esperada.

NO-GO si:

- El comando SIH no carga.
- Faltan archivos de configuración o plantillas SIH requeridas.
- Los archivos exportados son estructuralmente inválidos.

## 10. `.gitignore` y activos versionados

Objetivo: verificar que los datos generados estén ignorados sin ocultar configuraciones o plantillas versionadas.

Windows CMD:

```bat
git check-ignore -v configs\sih\selection_template.csv
git check-ignore -v configs\examples\main.yaml
git check-ignore -v outputs\demo.csv
git check-ignore -v runs\demo.csv
git check-ignore -v database\demo.csv
```

Resultado esperado:

- Los archivos dentro de `configs/` no deberían estar ignorados.
- Las rutas de salida generada, como `outputs/`, `runs/` y `database/`, deberían estar ignoradas.

NO-GO si:

- Plantillas o configuraciones de ejemplo requeridas quedan ocultas por `.gitignore`.
- Los directorios de datos generados no están ignorados.

## 11. Verificación de documentación de liberación

Objetivo: verificar que la documentación coincida con el alcance actual de producción.

Revisión manual:

```bat
type README.md
type docs\02_pipeline.md
type docs\03_cli.md
type docs\BATCH_GUIDE.md
type docs\CONFIGURATION_GUIDE.md
```

Resultado esperado:

- Las instrucciones de instalación están actualizadas.
- Los comandos CLI coinciden con los comandos implementados.
- El uso de batch está documentado.
- M9 no se presenta como listo para producción en esta liberación.

NO-GO si:

- La documentación indica ejecutar comandos que ya no existen.
- La documentación presenta funcionalidad experimental como lista para producción.
- Las verificaciones requeridas de liberación no están documentadas.

## Resumen final GO/NO-GO

GO si:

- La instalación limpia finaliza correctamente.
- Los imports críticos pasan.
- Los smoke tests del CLI pasan.
- `config-check` pasa.
- Los tests pasan.
- La verificación de compilación pasa.
- El smoke test de batch pasa.
- El pipeline local de producción funciona con datos reales.
- La exportación SIH se verifica cuando la entrega SIH está dentro del alcance.
- Las configuraciones y plantillas versionadas no quedan ocultas por `.gitignore`.

NO-GO si:

- Una instalación limpia no puede ejecutar `aforix --help`.
- Falta alguna dependencia runtime requerida.
- Los tests no pueden colectarse o ejecutarse.
- La orquestación batch no puede validar, planificar o ejecutar dry-run.
- Normalización o validación producen errores bloqueantes de calidad de datos.
- La documentación contradice el alcance real soportado en producción.
