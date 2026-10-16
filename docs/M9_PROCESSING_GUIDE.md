# Guía de procesamiento SonTek M9

Esta guía describe el flujo implementado en Aforix desde las exportaciones de RiverSurveyor Live hasta la preparación de archivos para el SIH. El código de instrumento en Aforix es `m9`; la fila SIH usada para el equipo de referencia de la prueba es `503, SonTek, 4980, M9, M9`.

## Alcance y criterio de medición

Aforix lee archivos `.mat` exportados por RiverSurveyor Live. El archivo nativo `.rivr` no se interpreta directamente; debe exportarse desde RiverSurveyor Live a MAT. La lectura actual usa el formato MAT compatible con SciPy; MAT v7.3/HDF5 no está soportado por este lector.

Cada MAT representa una transecta y se conserva como un registro independiente con su propio `Summary` y `Points`. **Aforix no promedia transectas distintas de un mismo aforo.** El promedio o combinación de pasadas no forma parte de la implementación actual y queda para una etapa futura con una regla validada.

Las muestras M9 se obtienen mientras el bote avanza por la sección. Por eso los `Points` son observaciones espaciotemporales del recorrido y no una tabla discreta de verticales medidas repetidamente en posiciones fijas. Dos transectas pueden tener distinto sentido de recorrido, número y ubicación de muestras, velocidad del bote, marcas de tiempo y trayectoria. Promediar filas por número de muestra o por una distancia aproximada podría combinar lugares y momentos diferentes y alterar profundidad, velocidad y caudal. Un promedio futuro necesitaría primero orientar y registrar espacialmente los perfiles, definir cómo reinterpolar puntos, tratar diferencias de cobertura y calidad y conservar la trazabilidad de las transectas de origen.

## Qué contiene el MAT y qué utiliza Aforix

Un MAT puede incluir estructuras de sitio, equipo, configuración, series acústicas, navegación y procesamiento. Los nombres presentes dependen de la versión y del contenido exportado. El adaptador requiere `SiteInfo`, `SystemHW`, `System` y `Summary`; usa estas estructuras y campos:

| Estructura o campo de RSL | Uso en Aforix |
| --- | --- |
| `SiteInfo.Station_Number`, `SiteInfo.Site_Name`, `SiteInfo.Comments` | Identificación, nombre y comentarios del sitio; los metadatos se resuelven además mediante `ingest.m9.metadata_policy`. |
| `SystemHW.SerialNumber`, `SystemHW.FirmwareVersion` | Serie y versión de firmware del equipo. |
| `System.Time` | Secuencia temporal de las muestras y fechas/horas de inicio y fin. |
| `Summary.Total_Q` | Caudal acumulado; el último valor finito es el caudal del transecto y la serie también se conserva por muestra. |
| `Summary.Area` | Área reportada por el equipo. |
| `Summary.Depth` | Profundidad por muestra; se calculan profundidad media y máxima. |
| `Summary.Track` | Posición de la embarcación; se proyecta a lo largo de la transecta para obtener progresiva y distancia de sección. |
| `Summary.Mean_Vel` | Velocidad horizontal media por muestra; si el sistema de coordenadas es ENU se proyecta a la normal de la transecta. |
| `Summary.Boat_Vel` | Componentes de velocidad de la embarcación, conservadas en `Points`. |
| `Setup.startEdge`, `Setup.coordinateSystem` | Sentido/orilla de inicio y sistema de coordenadas. `startEdge` permite orientar la distancia desde la margen izquierda. |
| `Setup.Edges_0__DistanceToBank`, `Setup.Edges_1__DistanceToBank` | Distancias de las muestras extremas a las márgenes, usadas en ancho y perímetro. |
| `GPS`, `Compass`, `System.Temperature/Heading` | Si existen en el MAT, se conservan coordenadas, inclinación/rumbo y temperatura disponibles por muestra. |

Las exportaciones pueden contener además `WaterTrack`, `BottomTrack`, `Processing` y otros datos internos. Que estén dentro del MAT no implica que todos se incorporen al esquema normalizado o a SIH: el alcance actual es el conjunto descrito en esta guía.

### Tablas que genera Aforix

- **Summary**: una fila por MAT/transecta. Incluye identificación y trazabilidad, inicio/fin, caudal, área, ancho, profundidad media/máxima, perímetro mojado, radio hidráulico, estado/motivo del IVE y datos de equipo.
- **Points**: una fila por muestra temporal. Incluye `sample_number`, `timestamp`, `elapsed_seconds`, `distance_along_transect_m`, `distance_m`, `width_m`, posición de track, profundidad, caudal acumulado e incremento, componentes de velocidad, velocidad normal, temperatura, rumbo, inclinación y GPS cuando estén disponibles.

En Points, `width_m` representa el ancho total de la sección repetido para asociar cada muestra con su aforo; **no** es el ancho de una celda ni el intervalo entre muestras. `distance_m` es la progresiva proyectada desde la margen física izquierda e incluye el desplazamiento a la orilla cuando el MAT lo informa.

El caudal SIH se mapea desde `Summary.q_total_m3s`. La velocidad media del Summary se deriva como caudal/área cuando el área es positiva. El ancho se obtiene de la trayectoria proyectada más las distancias de margen declaradas.

El perímetro mojado se estima con el perfil de profundidad de Points. Si el MAT informa una distancia positiva entre la margen seca y la muestra extrema, Aforix interpola un segmento recto desde profundidad cero. Si no hay distancia a la margen, no inventa ese tramo. El radio hidráulico se calcula como área del Summary dividida por el perímetro estimado. Es una estimación del perfil, no un valor independiente reportado por el instrumento.

## Procedimiento de ingesta a exportación

Ejecute los comandos desde la raíz del repositorio y con el entorno de Aforix activado. Coloque en `data/raw/M9/` los MAT que quiera procesar. La configuración de ejemplo habilita M9 y define `raw_subdir: M9`; los campos de estación, nombre, fecha y hora se controlan en `ingest.m9.metadata_policy` de `configs/examples/main.yaml`. Consulte [política de metadatos M9](M9_METADATA_POLICY.md) antes de cambiarla.

~~~powershell
aforix config-check -c configs/examples/main.yaml
aforix ingest m9 -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
aforix validate run -c configs/examples/main.yaml
~~~

1. **Ingesta** crea un run en `runs/ingest_m9/<id>/`, con Summary y Points canónicos por MAT bajo `outputs/raw_canonical/m9/`. Revise el resumen del run y `ingest_status.json`; un archivo MAT inválido no debe confundirse con uno procesado.
2. **build-groups** consolida las salidas de ingesta elegidas en `database/raw_canonical/m9/`. La política de selección de runs debe evitar mezclar una ingesta nueva con versiones antiguas.
3. **normalize** aplica `configs/normalization/m9.yaml` y escribe tablas normalizadas por instrumento en `database/normalized/m9/`, además de las tablas concatenadas globales si están habilitadas.
4. **validate** escribe reportes bajo `database/validation/`. Revise `validation_summary.csv` y `m9_validation.csv`; que el comando termine no significa que todos los registros estén aprobados.
5. **Exportación SIH**: revise `configs/sih/sih.yaml`, los catálogos de estación/instrumento/tipo/rango y el archivo de selección. El equipo de referencia usa instrumento 503, marca SonTek, serie 4980, modelo M9, tipo de aforo BOTE y rango ADCP. Cada número de serie distinto debe tener una entrada SIH correcta.

Ejemplo de exportación con archivo de selección explícito:

~~~powershell
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml --selection-file configs/sih/selection_template.csv
~~~

El exportador solicita confirmar la configuración SIH/IVE de cada instrumento; agregue `--yes` solo cuando quiera confirmar automáticamente los valores mostrados. Para dos MAT que comparten estación/fecha/hora, incluya `source_file` en la selección y copie la ruta exacta de la fila deseada en Summary. Aforix no elige automáticamente entre original y reprocesado ni da preferencia al sufijo `r`.

La exportación escribe archivos CSV de actuaciones y aforos en `outputs/sih/`, un manifiesto `sih_export_metadata.csv` y, si se puede calcular IVE, un libro de detalle en `outputs/sih/incertidumbre/`. El estado y motivo del IVE quedan registrados aunque no se genere el libro. Esta etapa prepara archivos para importar; no realiza una conexión ni carga al servidor SIH.

Para auditar una colección local aislada, sin reemplazar la base existente ni tocar los MAT originales:

~~~powershell
python scripts/audit_m9_local.py --raw-dir .\data\raw\M9 --exclude 20170901153604.mat
~~~

La exclusión debe ser intencional y queda registrada. El script crea una carpeta de auditoría en `runs/audit_m9/`, procesa las etapas y coteja las exportaciones. En la ejecución auditada el 16/10/2026 se procesaron 181 MAT, se revisaron 125 exportaciones y el manifiesto reportó 107 `OK`, 74 `REVISAR` y 1 `EXCLUIDO`. Esos conteos describen esa colección concreta, no un resultado esperado para cualquier conjunto de datos.

## IVE para M9: cálculo adaptado y límites

Aforix calcula IVE en la exportación desde Points normalizados, mediante el mismo motor de incertidumbre utilizado para perfiles discretos de otros instrumentos. Para M9 se trata de una **adaptación operativa**, no del algoritmo QRev ni de una incertidumbre certificada por SonTek. El cálculo preliminar que puede aparecer en Summary tampoco sustituye la evaluación que hace el exportador con la configuración SIH efectiva.

Para el perfil, Aforix proyecta `Mean_Vel` horizontal a la normal de la transecta. La implementación solo valida esa proyección para el sistema de coordenadas **ENU (código 2)**. El motor integra distancia, profundidad y velocidad normal por áreas *mid-section*. La configuración SIH vigente usa borde izquierdo y derecho en cero; cuando faltan los extremos físicos, agrega nodos sintéticos secos con profundidad y velocidad cero. Luego estima la incertidumbre con los componentes sistemático, ancho, profundidad y velocidad del método común de Aforix. Los parámetros documentados son sistemático 1 %, ancho 0,5 % por vertical y desviación mínima de profundidad 0,01 m; para velocidad se usa `s_v,IVE` sin piso instrumental. El caudal del IVE, `Q_mid`, es el integrado desde Points y puede diferir del caudal del fabricante en Summary. En SIH, `incertidumbre_IVE` se expresa en porcentaje y `error_IVE` en m³/s respecto de `Q_mid`.

### Cuándo no se calcula IVE

El IVE queda `not_available` o `not_applicable` cuando se presenta alguna de estas condiciones:

| Condición | Por qué impide el cálculo | Qué revisar |
| --- | --- | --- |
| El sistema de coordenadas no es ENU código 2, o no se puede obtener una normal válida desde la trayectoria. | No se obtiene una velocidad normal compatible con la sección. | Verificar `Setup.coordinateSystem`, Track y la configuración de coordenadas en RiverSurveyor; no reinterpretar automáticamente XYZ/Beam como ENU. |
| Falta una serie necesaria, los largos de distancia/profundidad/velocidad no coinciden o hay valores ausentes/no finitos. | No se puede construir un perfil completo sin inventar o descartar muestras. | Comparar MAT, CSV Points y el mapeo de normalización; corregir la fuente si corresponde y reingerir. |
| El perfil tiene menos de dos posiciones utilizables, o la anchura no es única, positiva y finita; también impiden el cálculo las profundidades negativas y los puntos fuera del ancho. | La geometría no cumple las entradas requeridas por el motor. | Revisar track, distancias a márgenes, unidades y ancho en Summary/Points. |
| Dos o más muestras tienen exactamente la misma `distance_m`. | El motor común necesita una posición distinta por vertical; las muestras repetidas pueden tener profundidad o velocidad diferentes. | Revisar la trayectoria y las muestras contra el MAT. Si la repetición es real, conservar las muestras y reportar IVE no disponible; si se corrige el origen, reingerir. No promediar ni borrar automáticamente. |
| Hay menos de 10 verticales interiores. | El método implementado define ese umbral mínimo de aplicabilidad; los bordes sintéticos no cuentan como verticales. | IVE queda `not_applicable`; conservar el aforo y su resultado hidráulico, con la calidad/estado informado. |
| La integración produce `Q_mid = 0`. | La incertidumbre relativa divide por el valor absoluto de Q mid y no puede definirse para caudal nulo. | Revisar sentidos y velocidades del perfil; no sustituir Q mid por el Summary para forzar el cálculo. |

La ausencia del IVE no elimina la medición ni, por sí sola, impide generar los CSV SIH de actuación y aforo. Los campos IVE quedan vacíos y el estado/motivo se informa en los metadatos y en la calidad exportada. Las discrepancias de validación se revisan por separado.

### Distancias repetidas y promedios futuros

Las distancias repetidas son el caso específico que impide usar actualmente Points M9 para IVE: convertir varias observaciones en una sola vertical requeriría decidir cómo combinar profundidad, velocidad y caudal incremental. Aforix conserva todas las filas y explica la causa; no selecciona una fila, promedia, interpola ni descarta muestras para obtener un número.

La misma cautela se aplica a promediar distintas transectas. El Summary del MAT es el resumen que RiverSurveyor entrega para **esa transecta**; no equivale a un promedio de varias pasadas. Una futura agregación deberá definir alineación espacial, tratamiento de sentidos/orillas, datos incompletos, criterios de selección y propagación de incertidumbre, y deberá verificarse con datos de referencia antes de habilitarse.

## Interpretación de estados y entrega

- `calculated`: el método implementado produjo incertidumbre absoluta, relativa y una categoría de calidad.
- `not_applicable`: no se alcanzó el mínimo de 10 verticales interiores.
- `not_available`: el perfil no permite el cálculo, hay posiciones repetidas, no se derivó velocidad normal o el caudal integrado es cero.
- `REVISAR`: Aforix preserva los datos y describe la incidencia y acción; requiere evaluación del usuario.
- `ERROR`: discrepancia introducida por el proceso o fallo de exportación que debe corregirse antes de considerar esa salida confiable.

El procesamiento local y la generación de CSV han sido verificados con datos M9 reales. **No se probó la importación de esos archivos en el sistema SIH receptor**, y la validación hidrométrica independiente del IVE adaptado requiere aceptación aparte.
