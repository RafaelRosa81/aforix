# Troubleshooting del módulo SIH

Esta guía resume problemas frecuentes detectados durante el desarrollo y uso del módulo SIH.

La herramienta principal de diagnóstico es:

```text
outputs/sih/sih_export_metadata.csv
```

Siempre revisar este archivo después de una exportación.

## 1. No se generan archivos CSV

### Síntoma

No aparecen archivos:

```text
ID_*_actuacion_*.csv
ID_*_aforo_*.csv
```

### Revisar

1. Que exista `configs/sih/sih.yaml`.
2. Que exista `selection_template.csv` o que el modo interactivo haya generado un selection temporal.
3. Que la carpeta `database/normalized` tenga datos.
4. Que el instrumento exista en normalized.
5. Revisar `sih_export_metadata.csv`.

## 2. Error: selection file missing required columns

### Síntoma

El export falla inmediatamente.

### Causa

El archivo de selección no tiene todas las columnas requeridas.

### Columnas obligatorias

```text
station_id
measurement_date
measurement_time
instrument
export_id
```

### Solución

Corregir encabezados del CSV.

El modo interactivo genera automáticamente estas columnas.

## 3. No measurement found

### Síntoma

Metadata contiene:

```text
No measurement found for station=..., date=..., time=...
```

### Causa

La medición no pudo encontrarse en normalized.

### Revisar

- `station_id`
- `measurement_date`
- `measurement_time`
- `instrument`

### Problema frecuente

Formato inconsistente de fecha/hora.

Ejemplo problemático:

```text
measurement_date = 2025-01-19
measurement_time = 14:18
```

Formato recomendado:

```text
measurement_date = 20250119
measurement_time = 141800
```

### Problema real detectado

Durante el desarrollo se detectaron horas inconsistentes:

```text
94521
094521
```

El modo interactivo intenta normalizar automáticamente usando zero-padding a 6 dígitos:

```text
94521 -> 094521
```

Sin embargo, si el normalized tiene formatos inconsistentes o truncados, el matching todavía puede fallar.

### Verificación rápida Python

```python
import pandas as pd

df = pd.read_csv("database/normalized/molinete/Summary.csv")
print(df[["station_id", "measurement_date", "measurement_time"]].head())
```

## 4. Multiple measurements found

### Síntoma

Metadata contiene:

```text
Multiple measurements found for station=..., date=..., time=...
```

### Causa

Más de una fila coincide en normalized.

### Posibles razones

- mediciones duplicadas;
- múltiples instrumentos mezclados;
- timestamps truncados;
- datos normalizados inconsistentes.

### Solución

Verificar unicidad de:

```text
station_id + measurement_date + measurement_time
```

## 5. Instrument lookup failed

### Síntoma

Metadata contiene:

```text
Instrument lookup failed
```

### Causa

No hubo coincidencia en `instrumentos.csv`.

### Revisar

1. Que exista `configs/sih/instrumentos.csv`.
2. Que las columnas configuradas existan.
3. Que los valores del raw canonical coincidan exactamente.
4. Que el instrumento tenga `instrument_lookup_fields` configurados.

### Debug recomendado

Verificar valores reales en raw canonical:

```python
import pandas as pd

df = pd.read_csv("database/raw_canonical/molinete/Summary.csv")
print(df[["helice", "instrument"]].head())
```

Y luego revisar el lookup:

```python
lookup = pd.read_csv("configs/sih/instrumentos.csv")
print(lookup.head())
```

## 6. Instrument lookup returned multiple matches

### Síntoma

Más de una fila coincide en `instrumentos.csv`.

### Causa

Los criterios configurados no identifican un instrumento único.

### Solución

Agregar criterios más específicos:

- `nro_serie`
- `codigo`

Evitar usar solamente:

```text
modelo
```

si existen múltiples instrumentos iguales.

## 7. raw_canonical_found = False

### Síntoma

Metadata contiene:

```text
raw_canonical_found = False
```

### Causa

No pudo encontrarse la tabla raw canonical.

### Qué sucede

El export puede continuar, pero:

- observaciones pueden quedar vacías;
- escalas pueden quedar vacías;
- operador puede quedar vacío;
- radio hidráulico puede quedar vacío;
- matching de instrumento puede fallar.

### Revisar

```text
database/raw_canonical/{instrument}/Summary.csv
```

## 8. Encoding incorrecto en Excel

### Síntoma

Caracteres extraños:

```text
Ã³
Ã±
```

### Causa

Encoding incorrecto.

### Solución

Usar:

```yaml
encoding: utf-8-sig
```

que es el valor actual por defecto.

## 9. Error por delimitador CSV

### Síntoma

Excel abre todo en una sola columna.

### Causa

Separador incorrecto.

### Solución

Revisar:

```yaml
output:
  delimiter: ","
```

En algunos entornos Windows puede requerirse:

```yaml
delimiter: ";"
```

según configuración regional.

## 10. Campos SIH vacíos

### Síntoma

Campos exportados vacíos.

### Causa frecuente

La columna configurada no existe.

Ejemplo:

```yaml
raw_canonical_fields:
  radio_hidraulico: radio_hidraulico_m
```

pero la columna no existe en raw canonical.

### Solución

Verificar columnas reales:

```python
import pandas as pd

df = pd.read_csv("database/raw_canonical/molinete/Summary.csv")
print(df.columns.tolist())
```

## 11. Instrumento no exportado

### Síntoma

No aparecen exports para un instrumento.

### Revisar

```yaml
instruments:
  <instrument>:
    enabled: true
```

Si está en `false`, el runner lo ignora.

El modo interactivo tampoco mostrará el instrumento.

## 12. Problemas con fechas y horas

### Problema actual conocido

Normalized puede contener formatos mixtos:

```text
2025-01-19
20250119
14:18:00
141800
94521
094521
```

El export intenta normalizar, pero esto puede generar errores ambiguos.

### Problema detectado específicamente

Molinete y archivos editados manualmente pueden producir horas sin cero inicial:

```text
94521
```

mientras otros instrumentos generan:

```text
094521
```

El modo interactivo normaliza automáticamente usando:

```text
zfill(6)
```

pero la recomendación sigue siendo estandarizar desde normalize.

### Recomendación futura

Estandarizar:

```text
measurement_date -> YYYYMMDD
measurement_time -> HHMMSS
```

## 13. Problemas con selection_template.csv

### Problema frecuente

Zero padding inconsistente.

Ejemplo:

```text
P1
P01
1
```

### Recomendación

Usar exactamente el mismo `station_id` presente en normalized.

## 14. Problemas con selection CSV interactivo

### Síntoma

El modo interactivo muestra mediciones pero el export falla después.

### Causa posible

El selection CSV temporal se generó correctamente, pero el runner batch posterior falló.

### Importante

El modo interactivo NO tiene lógica de exportación propia.

El flujo real es:

```text
interactive -> selection CSV temporal -> runner batch normal
```

Por eso:

- errores de matching;
- problemas de lookups;
- problemas de raw canonical;
- errores SIH;

pueden aparecer después de una selección interactiva aparentemente correcta.

### Revisar

1. `outputs/sih/_interactive_selection_*.csv`
2. `outputs/sih/sih_export_metadata.csv`
3. lookups SIH.

## 15. No aparecen instrumentos en modo interactivo

### Causa posible

Faltan columnas requeridas en normalized.

Columnas mínimas:

```text
station_id
measurement_date
measurement_time
```

### Qué hace el interactivo

El interactivo omite instrumentos inválidos automáticamente.

### Solución

Verificar:

```python
import pandas as pd

df = pd.read_csv("database/normalized/molinete/Summary.csv")
print(df.columns.tolist())
```

## 16. El preview interactivo queda vacío

### Causa posible

Los filtros eliminaron todas las mediciones.

### Revisar

- instrumentos seleccionados;
- estaciones seleccionadas;
- fecha inicial/final;
- datos realmente disponibles.

## 17. Problemas con lookups faltantes

### Síntoma

Falla al iniciar export.

### Causa

No existe alguno de:

```text
configs/sih/instrumentos.csv
configs/sih/tipos_aforos.csv
configs/sih/instrumentos_rangos.csv
```

### Solución

Crear los archivos y verificar rutas en `sih.yaml`.

## 18. Cómo revisar rápidamente los datos disponibles

### Normalized

```python
import pandas as pd

df = pd.read_csv("database/normalized/Summary.csv")
print(df[["station_id", "measurement_date", "measurement_time", "instrument"]].head())
```

### Raw canonical

```python
import pandas as pd

df = pd.read_csv("database/raw_canonical/molinete/Summary.csv")
print(df.head())
```

### Metadata SIH

```python
import pandas as pd

df = pd.read_csv("outputs/sih/sih_export_metadata.csv")
print(df)
```

### Selection interactivo generado

```python
import pandas as pd

df = pd.read_csv("outputs/sih/_interactive_selection_20260506_231500.csv")
print(df)
```

## 19. Diferencia entre errores recoverable y fatal

### Fatal

Detienen toda la corrida:

- YAML inválido;
- selection file inválido;
- normalized inexistente.

### Recoverable

Afectan solo una fila:

- no measurement found;
- lookup ambiguo;
- raw canonical faltante;
- lookup sin match.

En esos casos, el runner continúa con las demás filas y registra el error en metadata.

## 20. Buenas prácticas operativas

1. Ejecutar normalize antes de exportar.
2. Verificar `database/normalized`.
3. Verificar `database/raw_canonical`.
4. Revisar lookups antes de exportar.
5. Probar primero pocas mediciones en modo interactivo.
6. Revisar `outputs/sih/_interactive_selection_*.csv`.
7. Revisar `sih_export_metadata.csv`.
8. Mantener formatos consistentes de fecha/hora.
9. Evitar duplicados en normalized.
10. Usar matching de instrumento específico.
11. Versionar cambios en `sih.yaml` y lookups.
