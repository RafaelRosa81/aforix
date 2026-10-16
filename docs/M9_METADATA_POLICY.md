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

## Verificación

La política predeterminada se probó con 181 MAT reales en Windows. La ingesta produjo 362 CSV idénticos al run de referencia, salvo los metadatos propios de ejecución `run_id` y `source_run_dir`. Las pruebas también verifican que los valores definidos en YAML se apliquen a Summary, Points y nombres de salida.

Para instrucciones de uso M9 desde MAT hasta SIH, consulte [M9_PROCESSING_GUIDE.md](M9_PROCESSING_GUIDE.md). Los resultados generales de aceptación están en [M9_ACCEPTANCE.md](M9_ACCEPTANCE.md).