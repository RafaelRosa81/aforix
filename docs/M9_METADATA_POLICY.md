# Metadatos configurables en la ingesta M9

`ingest.m9.metadata_policy` utiliza el mismo motor de extracción que los demás
instrumentos. Controla `station_id`, `station_name`, `measurement_date` y
`measurement_time`. Las reglas admiten fuentes `raw_field`, `constant`,
`filename_regex` y `path_regex`, prioridad `first_non_empty`, transformaciones
y normalización del motor compartido.

## Compatibilidad predeterminada

La configuración de `configs/examples/main.yaml` conserva la identidad y los
nombres de salida de la ingesta anterior. Antes de aplicar la política se
mantiene la limpieza M9 del identificador (por ejemplo `133.0` → `133`, sin
convertir `P71` en otro número de estación). `uppercase: false` conserva la
capitalización del origen. La alternativa por carpeta sigue buscando el padre
más cercano de forma `P` seguido de 1 a 4 dígitos. Sin identificación se usa
`UNKNOWN`.

El contexto de `raw_field` contiene los campos del Summary interpretado y:

| Clave | Valor |
|---|---|
| `station_id` | Identificador del MAT con limpieza previa M9; vacío si no está presente |
| `fallback_station_id` | Identificador de carpeta o cadena vacía |
| `station_name` | Nombre del MAT |
| `measurement_date` | Inicio local, `YYYYMMDD` |
| `measurement_time` | Inicio local, `HHMMSS` |
| `measurement_start` | Inicio ISO 8601, con zona horaria |
| `filename`, `stem` | Nombre del MAT con extensión y sin ella |

La fecha y hora predeterminadas se preparan desde el inicio ya interpretado en
`project.timezone`; no hay una conversión adicional a UTC. Se usan campos
separados para evitar ambigüedades con formatos y zonas horarias. Si una regla
necesita `measurement_start`, puede usar `%Y-%m-%dT%H:%M:%S%z` como formato de
entrada (o `%Y-%m-%dT%H:%M:%S.%f%z` si incluye fracciones de segundo).

Sin bloque de política, o para campos no configurados, se conserva el
comportamiento anterior. Los resultados vacíos retornados por el motor usan
el respaldo anterior, igual que en FlowTracker. Las reglas inválidas generan
un error de ingesta registrado en `ingest_status.json`. Los normalizadores
conservan su semántica compartida: una regla de hora explícita sin valor puede
producir `000000`; para conservar el inicio original, omita esa regla o use
`measurement_time` como fuente. No se modificó el motor compartido.

## Ejemplo de cambio intencional

Para establecer un nombre de estación en una configuración de prueba:

```yaml
ingest:
  m9:
    enabled: true
    raw_subdir: M9
    metadata_policy:
      station_name:
        strategy: first_non_empty
        sources:
          - type: constant
            value: Pasarela de prueba
        transforms:
          - strip
```

Los otros tres metadatos conservan sus valores anteriores. Una modificación
de estación, fecha u hora afecta tanto Summary como Points, los nombres de
archivo y las claves posteriores de agrupación y selección. Mantenga las
salidas de fecha y hora en `%Y%m%d` y `%H%M%S` y use identificadores aptos para
nombres de archivo. La fecha y hora de fin siguen procediendo del MAT: cambiar
el inicio en una política no desplaza automáticamente el final del aforo.

Fabricante (`SonTek`), modelo (`M9`), extensión MAT, grupos de salida, muestras
y cálculos hidráulicos no cambian en esta refactorización. Tampoco cambian
normalización, IVE ni exportación SIH.

## Verificación y comparación local

Pruebas focalizadas:

```powershell
python -m pytest -q tests/test_metadata.py tests/test_ingest_station_id_boundary.py tests/test_m9_mat_adapter.py tests/test_m9_cli.py tests/test_m9_metadata_policy.py
python -m pytest -q
```

Comparación realizada antes/después sobre 7 MAT reales disponibles: mismos
nombres y contenido de los 14 CSV Summary/Points, ignorando únicamente
`run_id` y `source_run_dir`. Incluye cuatro transectos válidos, dos MAT con área
ausente y uno con perfiles nulos. Los archivos privados no se incorporan al repo.

Queda pendiente repetir la ingesta de los 181 MAT del usuario con las políticas
predeterminadas y compararla con `runs/ingest_m9/20261016_184249`. Conserve esa
carpeta de referencia. Ejecute `aforix ingest m9 -c configs/examples/main.yaml`
y use la ruta del nuevo run que imprime el comando. Compare primero el conjunto
de nombres CSV dentro de `outputs/raw_canonical/m9`, después todas las filas y
columnas como texto (para preservar ceros iniciales), excluyendo únicamente
`run_id` y `source_run_dir`. No ignore diferencias hidráulicas, de identidad ni
de `source_file`; use los mismos MAT en las mismas rutas para ambas ejecuciones.
No es necesario ejecutar build-groups ni normalize para esa comparación.

Para comparar sin modificar los CSV, sustituya `NUEVO_RUN` por el nombre que
imprimió la nueva ingesta y ejecute desde la raíz del repo:

```powershell
$anterior = ".\runs\ingest_m9\20261016_184249"
$nuevo = ".\runs\ingest_m9\NUEVO_RUN"
@'
import sys
from pathlib import Path
import pandas as pd
roots = [Path(x) / 'outputs/raw_canonical/m9' for x in sys.argv[1:]]
files = [{p.relative_to(r): p for p in r.rglob('*.csv')} for r in roots]
assert files[0] and files[0].keys() == files[1].keys(), 'Difieren los nombres o faltan CSV'
for name in sorted(files[0]):
    tables = [pd.read_csv(f[name], dtype=str, keep_default_na=False).drop(
        columns=['run_id', 'source_run_dir']) for f in files]
    pd.testing.assert_frame_equal(*tables, check_exact=True, obj=str(name))
print(f'PASS: {len(files[0])} CSV identicos salvo run_id/source_run_dir')
'@ | python - "$anterior" "$nuevo"
```

Una discrepancia detiene la comparación con un error. Mantenga ambos runs para
investigarla; no copie archivos de uno sobre el otro ni elimine diferencias.
