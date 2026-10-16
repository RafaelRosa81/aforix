# Auditoría local M9 hasta la exportación SIH

Este proceso verifica una colección local de MAT sin modificar los originales
ni la base operativa. No promedia transectos ni importa datos al servidor SIH.
Genera CSV y Excel de prueba y compara sus valores con Summary, Points y el
motor común IVE. La comprobación es de consistencia y trazabilidad del software;
no es una validación hidrométrica independiente del método IVE adaptado.

## Ejecución en PowerShell

Desde la raíz del repositorio, con el entorno aforix activado:

```powershell
git pull --ff-only origin feature/m9-ingest-normalization
python scripts/audit_m9_local.py --raw-dir .\data\raw\M9 --exclude 20170901153604.mat
```

La exclusión es explícita y queda registrada. El archivo de 2017 no se procesa
porque carece de muestras; se conserva intacto en raw. Los demás errores no se
ocultan: la auditoría registra cada MAT fallido y continúa con los que pudo ingerir.

Para comenzar solo con los cuatro MAT de julio de 2026:

```powershell
python scripts/audit_m9_local.py --raw-dir .\data\raw\M9 --pattern "20260703*r.mat"
```

Opciones:

- `--raw-dir`: carpeta de originales; incluye subcarpetas.
- `--pattern`: patrón de nombre, por defecto `*.mat`.
- `--exclude`: nombre exacto o ruta relativa con `/`; puede repetirse.
- `--output-root`: carpeta de resultados, por defecto `runs/audit_m9`.

Se usa una carpeta nueva por ejecución, identificada como `AUDIT_ROOT` al inicio.
Los MAT seleccionados se copian allí: prever espacio adicional para esas copias,
las tablas y los Excel. Se copia la configuración del repositorio local y se
limitan agrupación/normalización a M9. Se fuerzan las rutas de datos y resultados
a la carpeta aislada, incluso si la configuración habitual tiene rutas absolutas;
los nombres SIH de prueba incluyen un export_id único. Esa configuración queda guardada junto
con los resultados para reproducir la ejecución. No ejecutar instancias simultáneas
sobre la misma carpeta de salida interna; el script crea una distinta cada vez.

## Etapas y controles

1. Inventario con archivo original y SHA-256; exclusiones registradas.
2. Ingesta y registro individual de fallos. Agrupación y normalización aisladas.
3. Validación M9 de esquema, identidad, secuencia, rangos y consistencia hidráulica.
4. Selección SIH automática de claves no ambiguas. Si hay original y reprocesado
   con igual estación/fecha/hora, se conservan ambos y se bloquea su selección:
   no se elige una versión ni se promedian sus resultados.
5. Exportación local de prueba y revisión del manifiesto del exportador.
6. Comprobación de columnas y una fila por CSV; caudal, área, ancho, profundidad,
   velocidad media, radio hidráulico, estación, instrumento del catálogo y fechas.
7. Comprobación de estado, porcentaje, error absoluto y calidad IVE contra el motor;
   coincidencia CSV/XLSX, Q_mid y cantidad de puntos en el Excel. Si IVE no es
   calculable, los valores numéricos deben quedar vacíos y el caso queda para revisión.

El caudal de Summary no se sustituye por Q_mid ni se usa para reescalar error_IVE.
Los resultados de prueba pueden incluir casos REVISAR: no importar el directorio
completo al SIH sin revisar primero el manifiesto.

## Resultados

Dentro de `AUDIT_ROOT`:

- `audit_manifest.csv`: una fila por MAT, hash, estados por etapa, motivo y rutas
  a los CSV/XLSX. Las rutas source_file apuntan a los originales; las tablas
  procesadas conservan trazabilidad a las copias aisladas.
- `audit_issues.csv`: incidencias de validación por transecto, cuando se llegó a esa etapa.
- `audit_summary.json` y `LEEME.txt`: conteos y alcance de la comprobación.
- `01_ingest.log` a `05_export.log`: salida completa de cada etapa ejecutada.
- `database/normalized/m9`: Summary y Points nuevos, sin archivos de ejecuciones antiguas.
- `database/validation`: informes del validador.
- `outputs/sih`: aforos, actuaciones, informes Excel y metadata de exportación.
- `fatal_error.txt`: solo si hubo un fallo que impidió continuar el proceso general.

| Estado | Significado |
|---|---|
| OK | Controles locales aprobados, incluido IVE calculado y CSV/XLSX consistentes |
| REVISAR | Clave ambigua, incidencias de datos o IVE no calculable; requiere decisión técnica |
| ERROR | Fallo de procesamiento o discrepancia de resultados |
| EXCLUIDO | Fuera del conjunto evaluado por indicación explícita |

Código de salida: 0 si hay al menos un OK y no hay ERROR/REVISAR; 1 si hay
incidencias o ningún caso OK; 2 si los argumentos o la carpeta de entrada no son
válidos. EXCLUIDO nunca significa validado.

Para abrir y resumir la última auditoría:

```powershell
$ultima = Get-ChildItem .\runs\audit_m9 -Directory |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
$informe = Import-Csv (Join-Path $ultima.FullName "audit_manifest.csv")
$informe | Group-Object status | Select-Object Name, Count
$informe | Where-Object { $_.status -ne "OK" } |
    Select-Object source_file, status, validation, export, ive, message | Format-List
Invoke-Item $ultima.FullName
```

No publicar los resultados ni los MAT en GitHub. Para cerrar la aceptación del
cliente aún se requiere revisar los casos no OK y confirmar una importación real
al SIH de los aforos elegidos. El OK local no certifica esa importación ni la
exactitud física de la medición.
