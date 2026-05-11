# Auditoría final de producción (2026-05-11)

## Alcance
- Instrumentos en alcance productivo: FlowTracker, Molinete, Nivus.
- Fuera de alcance: M9/ADCP.
- Revisión sobre dependencias, CI, CLI, pipeline, batch, configuración, normalización, validación/auditoría, `.gitignore`, documentación y riesgos operativos.

## Hallazgos priorizados

### P1 — Riesgo de stale outputs en `build-groups` y `normalize`
**Evidencia**
- `build-groups` crea directorios y sobrescribe archivos coincidentes, pero no elimina archivos preexistentes que ya no están en la selección actual (`outdir.mkdir(..., exist_ok=True)` + escritura directa por nombre). `src/aforix/groups/build.py`
- `normalize` con `write_policy: overwrite` también sobrescribe por archivo, sin limpieza previa de directorio destino completo. `src/aforix/normalize/run.py`
- La config de ejemplo usa `overwrite`, lo cual no implica limpieza de sobrantes. `configs/examples/main.yaml`

**Impacto**
- Pueden quedar CSV antiguos mezclados con resultados nuevos en `database/raw_canonical`, `database/normalized` y posteriormente en validación/export.

**¿Afecta resultados?**
- Sí, potencialmente. Puede introducir duplicados o registros obsoletos en procesos aguas abajo.

**Acción recomendada**
- Operativamente, ejecutar limpieza previa controlada de destinos antes de cada corrida productiva.
- En PR pequeño futuro: agregar opción explícita `clean_output_before_write` por etapa (`build_groups`, `normalize`, opcionalmente `validation`) con comportamiento por defecto conservador.

### P2 — Cobertura CI útil pero mínima para release operacional
**Evidencia**
- El workflow CI ejecuta instalación, imports críticos, compile y `pytest -q` en Python 3.11. `.github/workflows/ci.yml`

**Impacto**
- Buena barrera inicial, pero no verifica corrida E2E del pipeline contra fixtures de integración.

**¿Afecta resultados?**
- Indirecto. Riesgo de regressions de integración no detectadas por smoke tests unitarios.

**Acción recomendada**
- Mantener como está para primera salida, y agregar luego 1 test de integración corto de pipeline (fixture mínimo por instrumento) en PR separado.

### P2 — Ingesta M9 habilitable en config, aunque fuera de alcance productivo
**Evidencia**
- Existe comando e implementación de `ingest m9` en CLI/código. `src/aforix/cli/main.py`, `src/aforix/ingest/m9.py`
- En config de ejemplo `m9.enabled: true`. `configs/examples/main.yaml`
- README declara M9 fuera de alcance productivo. `README.md`

**Impacto**
- Riesgo operativo de ejecución accidental de un instrumento fuera del alcance.

**¿Afecta resultados?**
- No directamente en FlowTracker/Molinete/Nivus si no se usa, pero sí riesgo de confusión operativa.

**Acción recomendada**
- Para operación inicial, fijar `m9.enabled: false` en config productiva (sin cambios de código).

### P3 — Warning de compatibilidad futura con pandas
**Evidencia**
- `pytest` reporta advertencia por `select_dtypes(include="object")` deprecado para comportamiento de strings. `src/aforix/normalize/transforms.py`

**Impacto**
- No bloquea hoy, pero puede romper al migrar a pandas futuro.

**¿Afecta resultados?**
- Actualmente no (solo warning).

**Acción recomendada**
- PR pequeño de compatibilidad para incluir explícitamente `str` según guía de pandas.

## Hallazgos revisados como no bloqueantes / falsos positivos
- Dependencias runtime críticas faltantes: **no observado**; están declaradas (`scikit-learn`, `scipy`, `matplotlib`, `psutil`). `pyproject.toml`
- Riesgo alto de versionar outputs generados: **mitigado** por `.gitignore` incluyendo `runs/`, `outputs/`, `data/`, `database/` y extensiones tabulares bajo esas raíces. `.gitignore`
- CLI fuera de Typer: **no observado**; CLI estructurada con Typer y subcomandos. `src/aforix/cli/main.py`
- Falta de config centralizada: **no observado**; comandos cargan YAML con `load_config`.

## Conclusión operativa
**Recomendación: GO con condiciones**.

### Condiciones exactas para producción inicial
1. Ejecutar limpieza previa controlada antes de cada corrida productiva sobre:
   - `database/raw_canonical/*`
   - `database/normalized/*`
   - `database/validation/*`
   preservando solo carpetas/archivos de control que se definan explícitamente.
2. Mantener `build_groups.use_latest_run_only: true` y deduplicación activa en config productiva.
3. Deshabilitar M9 en configuración productiva inicial (`m9.enabled: false`).
4. Conservar `aforix validate run` como gate obligatorio previo a export/analysis.

Bajo estas condiciones, el estado actual es apto para primera liberación operativa de FlowTracker, Molinete y Nivus.
