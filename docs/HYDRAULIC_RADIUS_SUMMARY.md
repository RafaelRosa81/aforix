# Radio hidráulico en Summary

## Contrato

El campo normalizado `hydraulic_radius_m` representa el radio hidráulico en metros, definido como el área mojada de la sección dividida por su perímetro mojado.

- **Nivus**: se conserva el valor informado por el instrumento, `rh [m]`, sin recalcularlo.
- **Molinete**: se conserva el valor `radio_hidraulico_m` leído de la celda inmediatamente a la derecha de la etiqueta «Radio Hidráulico» del Excel original.
- **FlowTracker**: se calcula a partir de `Points.distance_m` y `Points.depth_m` normalizados para cada combinación de instrumento, estación, fecha y hora. No se modifican los caudales, los valores IVE ni los campos de exportación SIH.

## Geometría FlowTracker: criterio aprobado

Los puntos extremos observados **delimitan la sección mojada**. Si la profundidad en cualquiera de esos extremos es positiva, se considera una **margen vertical** de esa profundidad en esa posición. No se extiende la sección más allá de las posiciones observadas ni se agregan puntos de profundidad cero artificiales.

Ordenando los puntos por distancia transversal `x_i`, con profundidades `h_i`:

```text
A = Σ (x[i+1] - x[i]) × (h[i] + h[i+1]) / 2
P = h[0] + Σ sqrt((x[i+1] - x[i])² + (h[i+1] - h[i])²) + h[n-1]
Rh = A / P
```

Las profundidades extremas se suman al perímetro **solo como longitud vertical de margen**; si valen cero, su aporte es nulo. El fondo se representa mediante segmentos rectos entre estaciones consecutivas. El cálculo del radio hidráulico rechaza geometrías con menos de dos estaciones, distancias repetidas con profundidades contradictorias, profundidades negativas, datos no numéricos o área mojada nula. **Para proteger los procesos existentes**, si una medida presenta geometría inválida, el enriquecimiento deja `hydraulic_radius_m` vacío (`NaN`) para esa medida y conserva las demás columnas de `Summary`; no interrumpe la normalización por esa causa. Los problemas de integridad de claves de identificación siguen siendo errores.

**Limitación**: esta definición supone que la sección está completamente delimitada por las estaciones extremas y que los tramos entre estaciones son lineales. La precisión depende de la densidad y calidad del levantamiento.

## Verticales repetidas en FlowTracker

Las filas de `Points` pueden repetir una distancia transversal porque existen varias observaciones de velocidad en una misma vertical. Para construir la geometría se consideran **una sola vez** las parejas idénticas `(distance_m, depth_m)`; las filas originales de `Points` permanecen intactas. Si una misma distancia contiene **profundidades distintas**, la geometría es ambigua: no se promedian y el radio queda vacío para esa medida.

La revisión de seis aforos reales con radio inicialmente vacío identificó exclusivamente repeticiones con la misma profundidad: estaciones 010120180517 (2018-05-17), 11901602_022 (2022-02-16), 7005 (2025-12-17 y 2026-01-22), 7008 (2025-12-15) y 70911 (2025-12-15). Estos casos deben reprocesarse con la corrección y contrastarse con los resultados anteriores.

## Verificación con aforos reales

Se recuperaron tres conjuntos de `Points` del archivo de trabajo `Template_incertidumbre_aforos_revisado.xlsx`, hojas `Points_1`, `Points_2` y `Points_3`. Se evaluó la geometría con el criterio anterior:

| Estación | Fecha | A (m²) | P (m) | Rh (m) |
|---|---|---:|---:|---:|
| 7003 | 2026-01-22 | 0.752 | 4.749242 | 0.158341 |
| 7013 | 2026-01-23 | 1.013 | 7.829056 | 0.129390 |
| 7014 | 2026-01-23 | 1.830 | 11.434437 | 0.160043 |

Para 7003, las profundidades de margen son 0.06 m y 0.14 m; ambas se incluyen como tramos verticales. Para 7013 y 7014 las profundidades extremas son cero.

Estos resultados son una **verificación geométrica con datos reales recuperados de una plantilla de trabajo**, no una prueba de aceptación completa de ingestión/normalización ni una comparación con un valor de radio hidráulico certificado por el equipo. Las pruebas automatizadas del repositorio verifican además los casos geométricos y la asociación por medida.

## Compatibilidad

Esta funcionalidad es aditiva a `Summary`. No debe modificar cálculos de incertidumbre IVE, estructura de SIH, valores históricos ni los demás campos normalizados. Antes de integrar, ejecutar toda la batería `pytest -q` y revisar cualquier consumidor que requiera una lista fija de columnas.
