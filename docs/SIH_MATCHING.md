# Matching del módulo SIH

Esta guía explica cómo el módulo SIH encuentra una medición de Aforix y cómo resuelve IDs externos mediante lookups.

El matching SIH tiene dos niveles:

1. Matching de medición: selección -> `database/normalized`.
2. Matching de instrumento SIH: raw canonical -> `instrumentos.csv`.

## 1. Matching de medición

Cada fila del archivo de selección debe identificar una medición concreta.

Columnas requeridas:

```text
station_id
measurement_date
measurement_time
instrument
export_id
```

El módulo usa estas columnas para buscar una única fila en `Summary.csv`.

## 2. Dónde busca Summary.csv

Para el instrumento indicado en la selección, el módulo busca en:

```text
database/normalized/{instrument}/Summary.csv
database/normalized/{instrument}/Summary/Summary.csv
database/normalized/Summary.csv
```

Si encuentra una tabla con columna `instrument`, filtra por el instrumento indicado.

Para raw canonical usa el mismo patrón:

```text
database/raw_canonical/{instrument}/Summary.csv
database/raw_canonical/{instrument}/Summary/Summary.csv
database/raw_canonical/Summary.csv
```

El normalized es obligatorio. El raw canonical es opcional, pero varios campos dependen de él.

## 3. Matching station/date/time

El matching contra normalized usa:

```text
station_id
measurement_date
measurement_time
```

La comparación de `station_id` es directa como string.

La fecha de normalized se normaliza quitando guiones:

```text
2025-01-19 -> 20250119
```

La hora de normalized se normaliza quitando `:` y `.` y tomando los primeros 6 caracteres:

```text
14:18:00 -> 141800
14.18.00 -> 141800
```

Por eso, en `selection_template.csv` se recomienda usar:

```text
measurement_date = YYYYMMDD
measurement_time = HHMMSS
```

Ejemplo:

```csv
station_id,measurement_date,measurement_time,instrument,export_id
P11,20260119,141800,molinete,0001
P8,20251215,124600,nivus,0002
```

## 4. Qué pasa si hay cero o múltiples mediciones

### 4.1 Cero matches

Si no encuentra la medición en normalized, se registra error en `sih_export_metadata.csv`.

El mensaje contiene una forma como:

```text
No measurement found for station=P11, date=20260119, time=141800
```

### 4.2 Múltiples matches

Si encuentra más de una fila para la misma combinación `station_id + measurement_date + measurement_time`, se registra error.

El mensaje contiene una forma como:

```text
Multiple measurements found for station=P11, date=20260119, time=141800
```

Esto indica que el normalized no identifica la medición de forma única.

## 5. Matching raw canonical

Después de resolver la medición normalizada, el módulo intenta resolver una fila equivalente en raw canonical.

Si no la encuentra:

- no falla automáticamente;
- `raw_measurement` queda vacío;
- `raw_canonical_found` en metadata queda `False`;
- los campos dependientes de raw canonical quedan vacíos;
- el matching de instrumento puede fallar si depende de campos raw.

## 6. Matching de instrumentos SIH

El campo `id_instrumento` se resuelve usando:

```text
configs/sih/instrumentos.csv
```

La configuración está en:

```yaml
lookup_tables:
  instrumentos:
    file: instrumentos
    value_column: id
    match_columns:
      - marca
      - nro_serie
      - modelo
      - codigo
```

Y por instrumento:

```yaml
instrument_lookup_fields:
  marca: null
  nro_serie: null
  modelo: instrument
  codigo: null
```

## 7. Significado de marca / nro_serie / modelo / codigo

Estas cuatro claves son criterios posibles para buscar un instrumento en `instrumentos.csv`.

| Clave | Significado conceptual | Dónde se usa |
| --- | --- | --- |
| `marca` | marca del instrumento | columna `marca` del lookup |
| `nro_serie` | número de serie | columna `nro_serie` del lookup |
| `modelo` | modelo o nombre del instrumento | columna `modelo` del lookup |
| `codigo` | código interno o identificador adicional | columna `codigo` del lookup |

En `instrument_lookup_fields`, cada una apunta a una columna de raw canonical.

Ejemplo:

```yaml
instrument_lookup_fields:
  marca: null
  nro_serie: helice
  modelo: molinete
  codigo: null
```

Esto significa:

- ignorar `marca`;
- leer `helice` desde raw canonical y compararlo contra `instrumentos.csv:nro_serie`;
- leer `molinete` desde raw canonical y compararlo contra `instrumentos.csv:modelo`;
- ignorar `codigo`.

## 8. Matching flexible paso a paso

Para resolver `id_instrumento`:

1. Carga `instrumentos.csv`.
2. Lee `lookup_tables.instrumentos.match_columns`.
3. Para cada columna de matching:
   - busca qué columna raw corresponde según `instrument_lookup_fields`;
   - si está en `null`, la ignora;
   - si raw canonical no existe, no puede leer valor;
   - si el valor raw está vacío, ignora ese criterio;
   - si hay valor, filtra el lookup por igualdad exacta.
4. Si no usó ningún criterio, falla.
5. Si después de filtrar no queda ninguna fila, falla.
6. Si queda más de una fila, falla.
7. Si queda una única fila, devuelve `value_column`, normalmente `id`.

## 9. Casos de error

### 9.1 No hay criterios configurados o poblados

Ocurre cuando todos los campos están en `null`, vacíos, o raw canonical no tiene valores útiles.

Mensaje esperado:

```text
Instrument lookup could not be resolved because no matching fields were configured/populated.
```

### 9.2 Cero matches

Ocurre cuando los valores raw no coinciden con ninguna fila de `instrumentos.csv`.

Mensaje esperado:

```text
Instrument lookup failed. Used criteria: ...
```

### 9.3 Múltiples matches

Ocurre cuando los criterios configurados son insuficientes y más de una fila del lookup coincide.

Mensaje esperado:

```text
Instrument lookup returned multiple matches. Used criteria: ...
```

Solución: agregar criterios más específicos, por ejemplo `nro_serie` o `codigo`.

## 10. Matching de tipo de aforo

`id_tipo_aforo` se resuelve así:

1. Si el instrumento tiene un valor directo configurado, se usa ese valor.
2. Si no, se usa `tipo_aforo_lookup` contra `tipos_aforos.csv`.

Ejemplo:

```yaml
tipo_aforo_lookup: Vadeo
```

El lookup usa:

```yaml
key_column: descripcion
value_column: id
```

## 11. Matching de instrumentos_rangos

`id_instrumentos_rangos` se resuelve usando:

```yaml
instrumentos_rangos_lookup: Velocimetro puntual
```

contra `instrumentos_rangos.csv`, usando:

```yaml
key_column: descripcion
value_column: id
```

Si no hay match y el lookup no es requerido en el código, puede quedar vacío.

## 12. Recomendaciones para configurar nuevos instrumentos

Para evitar errores de matching:

1. Asegurar que raw canonical tenga columnas estables para identificar el instrumento.
2. Usar al menos un criterio específico en `instrument_lookup_fields`.
3. Preferir `nro_serie` o `codigo` si existen.
4. Evitar depender solamente de `modelo` si hay múltiples instrumentos del mismo modelo.
5. Completar `instrumentos.csv` con valores exactamente iguales a los del raw canonical.
6. Revisar `sih_export_metadata.csv` después de cada corrida.

## 13. Recomendación de normalización futura

Para hacer el matching más robusto, conviene que Aforix unifique progresivamente:

```text
measurement_date -> YYYYMMDD
measurement_time -> HHMMSS
```

en las salidas normalizadas o, al menos, en los archivos de selección SIH.
