@echo off
setlocal

REM ============================================================
REM Custom Aforix batch launcher template
REM Copy this file, rename it, and edit BATCH_FILE.
REM ============================================================

set REPO_DIR=D:\repos\aforix
set CONDA_ENV=aforix
set CONDA_BAT=

REM Edit this path to point to your own YAML.
set BATCH_FILE=configs\batches\user\my_batch.yaml

if not "%CONDA_BAT%"=="" (
    call "%CONDA_BAT%" activate %CONDA_ENV%
) else (
    call conda activate %CONDA_ENV%
)

if errorlevel 1 (
    echo.
    echo Failed to activate conda environment: %CONDA_ENV%
    echo Edit CONDA_BAT if conda is not globally available.
    pause
    exit /b 1
)

cd /d "%REPO_DIR%"

echo.
echo Running custom Aforix batch:
echo %BATCH_FILE%
echo.

aforix batch check -b "%BATCH_FILE%"
if errorlevel 1 goto failed

aforix batch plan -b "%BATCH_FILE%"
if errorlevel 1 goto failed

aforix batch run -b "%BATCH_FILE%"
if errorlevel 1 goto failed

echo.
echo Batch finished successfully.
echo Check runs\batch for manifest.json.
pause
exit /b 0

:failed
echo.
echo Batch failed.
pause
exit /b 1