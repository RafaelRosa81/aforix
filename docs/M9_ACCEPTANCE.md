# Verificación M9 — 16 de octubre de 2026

## Alcance y decisión de entrega

Se ejecutó el CLI completo en un proyecto temporal limpio con cuatro MAT reales
RiverSurveyor Live, estación 133, SonTek M9 serie 4980. No se promedian transectos.
El recorrido ingesta → build-groups → normalización → exportación SIH pasó las
comprobaciones de trazabilidad, conteos, caudal, radio hidráulico e IVE.
Esto habilita una prueba de aceptación local. La entrega definitiva requiere
repetirla en Windows y confirmar la importación de los CSV en el SIH del cliente.
No se verificó una conexión ni una carga real al SIH.

## Hallazgos corregidos

- `Setup.startEdge`: 0 izquierda, 1 derecha. Se invierte la progresiva de los
  transectos que empiezan a la derecha; los offsets izquierdo/derecho se asignan
  a la margen física correcta al calcular el perímetro mojado.
  Referencia: SonTek RiverSurveyor Live User Manual, revisión 2022, Appendix C:
  https://info.xylem.com/rs/240-UTB-146/images/rsl-manual.pdf
- El IVE preliminar de ingesta delega al mismo motor de la exportación.
  No descarta muestras inválidas ni posiciones duplicadas para obtener un resultado.
- Las unidades explícitas no SI se rechazan; no se convierten silenciosamente.
  Si el MAT no declara unidades, se mantiene el supuesto histórico SI.
- Solo se deriva velocidad normal para coordenadas ENU (código 2).
  XYZ/Beam no habilitan este cálculo sin una transformación validada.
- Los fallos de ingesta generan `ingest_status.json` y salida con error.
- `tzdata` es dependencia explícita para resolver zonas horarias en Windows.
- Se corrigió la documentación: `incertidumbre_IVE` exportada es porcentaje.
- Los Points M9 de otro `source_file` no se utilizan como sustituto del MAT solicitado.

## Pruebas automatizadas

`python -m pytest -q`: 326 aprobadas, 4 omitidas; 23 avisos de deprecación
de pandas. Se cubren también regresiones de los otros instrumentos.

## Resultados con márgenes corregidas

| Inicio | Muestras | Caudal SIH m³/s | Radio m | IVE % | Error IVE m³/s |
|---|---:|---:|---:|---:|---:|
| 11:17:21 | 281 | 4.715018498 | 0.892821063 | 1.915032676 | 0.096598715 |
| 11:23:45 | 157 | 5.028343663 | 0.978510224 | 3.670255242 | 0.191381237 |
| 11:27:06 | 182 | 5.664091985 | 0.976741921 | 3.190490979 | 0.191338685 |
| 11:30:24 | 138 | 5.070337733 | 0.993061540 | 3.776879797 | 0.201103757 |

Resultado: 4 filas Summary, 4 archivos Points, 758 muestras, 4 CSV aforo,
4 CSV actuación, 4 informes Excel IVE y un manifiesto de exportación.
Los cuatro estados IVE son `calculated`; el instrumento SIH es 503.

## Coherencia con los demás instrumentos

`caudal` conserva `Summary.q_total_m3s`. El motor común integra sus propios
Points para obtener `Q_mid`. `error_IVE` es la incertidumbre absoluta de ese
motor y `incertidumbre_IVE = 100 * error_IVE / abs(Q_mid)`.
No se reescala el error usando el caudal de Summary.

El Summary preliminar conserva `uncertainty_ive_relative` como fracción;
el SIH la calcula nuevamente y la expresa como porcentaje. La ingesta usa
márgenes cero y los parámetros por defecto; la exportación aplica la
configuración SIH vigente. Con los mismos parámetros ambos cálculos coinciden.

El radio es área reportada / perímetro del perfil, con interpolación lineal a
las márgenes. Es una estimación dependiente del perfil medido, no un valor
certificado por el fabricante. El IVE sobre muestras M9 sigue siendo una
adaptación del método de Aforix, no una incertidumbre QRev.

## Repetición local sin tocar la base existente

Desde la raíz del repo y con el entorno activado:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/audit_m9_acceptance.py --raw-dir .\data\raw\M9
```

El script copia los MAT directamente contenidos en esa carpeta a un proyecto
temporal, ejecuta los cuatro comandos y muestra `ACCEPTANCE_ROOT` para revisar
sus resultados. Requiere una colección de transectos con IVE calculable y claves
de selección distintas. No modifica la base actual ni envía archivos al SIH.

Antes de regenerar la base operativa, respaldar y apartar los resultados M9
antiguos de raw_canonical y normalized. `overwrite` reemplaza archivos de igual
nombre, pero no elimina otros nombres antiguos. Las copias compatibles se
resuelven al seleccionar Points; copias con valores contradictorios bloquean IVE.
No borrar los MAT fuente. Después ejecutar ingesta, build-groups, normalización
y exportación usando la configuración habitual.

## Límites y pendientes de aceptación

- Verificado con estos cuatro MAT SI/ENU; no con todos los formatos/versiones
  de RiverSurveyor. MAT v7.3/HDF5 no está soportado por este lector.
- Si falta `startEdge`, se asume izquierda por compatibilidad; revisar ese dato
  en archivos distintos de la colección ensayada.
- Dos transectos con idénticos instrumento/estación/fecha/hora se conservan en
  ingesta, pero la selección SIH actual los considera ambiguos y bloquea exportación.
- La validación genérica de Points contiene columnas de instrumentos discretos
  (`point_index`, `area_m2`, `q_m3s`) que M9 no proporciona. No usar ese informe
  genérico como criterio único de aceptación M9; esta auditoría valida su esquema.
- La incertidumbre depende de que la progresiva proyectada describa una sección
  interpretable. Posiciones repetidas o datos no finitos impiden IVE.
- Validar con el cliente el carácter adaptado de IVE y el radio estimado, y
  comprobar una importación real al SIH antes de cerrar la entrega.
