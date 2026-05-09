# Guía de launchers de Aforix

Esta guía explica cómo usar los launchers de Aforix para abrir la CLI, ejecutar pipelines batch predeterminados y ejecutar archivos batch YAML personalizados sin escribir comandos largos.

Los launchers son envoltorios de conveniencia. No implementan lógica de procesamiento.

Solo hacen lo siguiente:

- activar el entorno configurado;
- moverse a la carpeta del repositorio de Aforix;
- ejecutar comandos existentes de `aforix` o archivos batch YAML;
- mantener la terminal visible para que el usuario pueda leer mensajes y errores.

---

## 1. Carpetas de launchers

Los launchers están en:

```text
launchers/
├── windows/
└── linux/
```

Los launchers de Windows usan archivos `.bat`.

Los launchers de Linux usan archivos `.sh`.

---

## 2. Launchers disponibles para Windows

```text
launchers/windows/aforix_shell.bat
launchers/windows/run_batch_file.bat
launchers/windows/run_custom_batch_template.bat
launchers/windows/run_consolidated_pipeline.bat
launchers/windows/run_full_ingest_pipeline.bat
launchers/windows/run_analysis_pipeline.bat
launchers/windows/run_sih_export.bat
```

### 2.1 `aforix_shell.bat`

Abre una terminal con el entorno Conda `aforix` activado y con el directorio de trabajo ubicado en el repositorio de Aforix.

Usalo cuando quieras escribir comandos manualmente.

### 2.2 `run_batch_file.bat`

Ejecuta cualquier archivo batch YAML.

Uso desde CMD:

```bat
launchers\windows\run_batch_file.bat configs\batches\examples\check_only.yaml
```

También podés arrastrar y soltar un archivo `.yaml` sobre este launcher.

Si no se pasa una ruta YAML, el launcher la pide por consola.

### 2.3 `run_custom_batch_template.bat`

Plantilla para crear un botón personal de doble clic.

Copiá el archivo, cambiale el nombre y editá:

```bat
set BATCH_FILE=configs\batches\user\my_batch.yaml
```

Ejemplos de copias:

```text
run_my_correlation.bat
run_my_sih_export.bat
run_my_monthly_summary.bat
```

### 2.4 Launchers predeterminados para Windows

Estos ejecutan pipelines de ejemplo ya existentes:

```text
run_consolidated_pipeline.bat  -> configs/batches/examples/consolidated_data_pipeline.yaml
run_full_ingest_pipeline.bat   -> configs/batches/examples/full_ingest_pipeline.yaml
run_analysis_pipeline.bat      -> configs/batches/examples/analysis_pipeline.yaml
run_sih_export.bat             -> configs/batches/examples/sih_export_pipeline.yaml
```

---

## 3. Launchers disponibles para Linux

```text
launchers/linux/aforix_shell.sh
launchers/linux/run_batch_file.sh
launchers/linux/run_custom_batch_template.sh
launchers/linux/run_consolidated_pipeline.sh
launchers/linux/run_full_ingest_pipeline.sh
launchers/linux/run_analysis_pipeline.sh
launchers/linux/run_sih_export.sh
```

Antes del primer uso:

```bash
chmod +x launchers/linux/*.sh
```

### 3.1 `aforix_shell.sh`

Abre una shell lista para usar Aforix.

```bash
./launchers/linux/aforix_shell.sh
```

### 3.2 `run_batch_file.sh`

Ejecuta cualquier archivo batch YAML.

```bash
./launchers/linux/run_batch_file.sh configs/batches/examples/check_only.yaml
```

Si no se pasa una ruta YAML, el launcher la pide por consola.

### 3.3 `run_custom_batch_template.sh`

Plantilla para crear un launcher personal.

Copiar y renombrar:

```bash
cp launchers/linux/run_custom_batch_template.sh launchers/linux/run_my_batch.sh
```

Luego editar:

```bash
BATCH_FILE="${BATCH_FILE:-configs/batches/user/my_batch.yaml}"
```

### 3.4 Launchers predeterminados para Linux

```text
run_consolidated_pipeline.sh  -> configs/batches/examples/consolidated_data_pipeline.yaml
run_full_ingest_pipeline.sh   -> configs/batches/examples/full_ingest_pipeline.yaml
run_analysis_pipeline.sh      -> configs/batches/examples/analysis_pipeline.yaml
run_sih_export.sh             -> configs/batches/examples/sih_export_pipeline.yaml
```

---

## 4. Configurar rutas y Conda

Cada launcher tiene variables editables cerca del inicio del archivo.

### Windows

```bat
set REPO_DIR=D:\repos\aforix
set CONDA_ENV=aforix
set CONDA_BAT=
```

Si `conda activate aforix` funciona en CMD, `CONDA_BAT` puede quedar vacío.

Si Conda no está disponible globalmente, definí la ruta explícitamente, por ejemplo:

```bat
set CONDA_BAT=C:\Users\%USERNAME%\miniconda3\condabin\conda.bat
```

o:

```bat
set CONDA_BAT=C:\ProgramData\miniconda3\condabin\conda.bat
```

### Linux

```bash
REPO_DIR="${REPO_DIR:-$HOME/repos/aforix}"
CONDA_ENV="${CONDA_ENV:-aforix}"
CONDA_SH="${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
```

Podés sobrescribir variables al ejecutar:

```bash
REPO_DIR=/data/repos/aforix CONDA_ENV=aforix ./launchers/linux/run_batch_file.sh configs/batches/examples/check_only.yaml
```

---

## 5. Dónde están los archivos batch YAML

Ejemplos oficiales:

```text
configs/batches/examples/
```

Ejemplos atómicos por funcionalidad:

```text
configs/batches/examples/atomic/
```

Batches definidos por el usuario:

```text
configs/batches/user/
```

Flujo recomendado:

1. Copiar un YAML de ejemplo.
2. Pegar la copia en `configs/batches/user/`.
3. Cambiarle el nombre.
4. Editar parámetros.
5. Validar con `batch check`.
6. Ejecutar con CLI o con launcher.

Ejemplo:

```bash
aforix batch check -b configs/batches/user/my_batch.yaml
aforix batch plan -b configs/batches/user/my_batch.yaml
aforix batch run -b configs/batches/user/my_batch.yaml --dry-run
aforix batch run -b configs/batches/user/my_batch.yaml
```

---

## 6. Ejecutar un batch personalizado con doble clic

### Windows opción A: arrastrar y soltar

Arrastrá tu archivo YAML sobre:

```text
launchers/windows/run_batch_file.bat
```

### Windows opción B: botón personal fijo

Copiá:

```text
launchers/windows/run_custom_batch_template.bat
```

Renombralo y editá:

```bat
set BATCH_FILE=configs\batches\user\my_batch.yaml
```

Luego hacé doble clic sobre ese `.bat`.

### Linux

Usá:

```bash
./launchers/linux/run_batch_file.sh configs/batches/user/my_batch.yaml
```

O copiá:

```text
launchers/linux/run_custom_batch_template.sh
```

y editá `BATCH_FILE`.

---

## 7. Ejemplo de acceso directo Linux `.desktop`

Se incluye un ejemplo en:

```text
launchers/linux/desktop_examples/aforix_batch.desktop.example
```

Para usarlo:

1. Copiarlo al escritorio o al directorio de lanzadores de aplicaciones.
2. Renombrarlo a `.desktop`.
3. Editar `Exec` y `Path`.
4. Darle permisos de ejecución.

Ejemplo:

```bash
chmod +x aforix_batch.desktop
```

El acceso directo debe usar:

```ini
Terminal=true
```

para que el usuario pueda ver errores y progreso.

---

## 8. Outputs y manifests

Las corridas batch escriben resultados operativos en:

```text
runs/batch/<batch_run_id>/manifest.json
```

El manifest registra:

- estado de la corrida;
- duración;
- outputs;
- warnings;
- errores;
- métricas de CPU/RAM;
- tamaños de entrada/salida;
- filas procesadas;
- archivos escritos.

Siempre conviene revisar el manifest después de corridas importantes.

---

## 9. Solución de problemas

### 9.1 Falla la activación de Conda

Revisar:

- `CONDA_ENV`;
- `CONDA_BAT` en Windows;
- `CONDA_SH` en Linux;
- que el entorno exista.

### 9.2 No se encuentra el YAML

Revisar la ruta relativa a la raíz del repositorio.

Ejemplo:

```text
configs/batches/user/my_batch.yaml
```

### 9.3 Falla `batch check`

Ejecutar manualmente:

```bash
aforix batch check -b <batch.yaml>
```

Causas comunes:

- indentación YAML inválida;
- nombre de comando incorrecto;
- faltan parámetros requeridos;
- referencia incorrecta a variables.

### 9.4 El batch termina bien pero no escribe archivos

Revisar los warnings en:

```text
runs/batch/<batch_run_id>/manifest.json
```

Algunos análisis pueden terminar correctamente pero no escribir archivos si los filtros son demasiado restrictivos o si los datos no se cruzan.

### 9.5 La terminal se cierra demasiado rápido

Usar los launchers provistos. Están diseñados para mantener la terminal visible, especialmente en Windows.

---

## 10. Workflows interactivos

Los launchers actuales ejecutan archivos batch YAML existentes.

En el futuro se podrá agregar un comando interactivo guiado, por ejemplo:

```bash
aforix interactive
aforix interactive --section correlation
aforix interactive --section export-tables
```

Hasta que eso esté implementado, el flujo recomendado es:

1. editar un archivo YAML;
2. ejecutarlo con `run_batch_file`;
3. revisar el manifest.
