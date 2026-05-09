@echo off
setlocal

REM ============================================================
REM Run any Aforix batch YAML file
REM Supports drag-and-drop or manual path input.
REM ============================================================

set REPO_DIR=D:\repos\aforix
set CONDA_ENV=aforix
set CONDA_BAT=

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

if "%~1"=="" (
    echo.
    echo No batch YAML file was provided.
    echo You can drag a YAML file onto this launcher,
    echo or type a path now.
    echo.
    set /p BATCH_FILE=Batch YAML path: 
) else (
    set BATCH_FILE=%~1
)

if "%BATCH_FILE%"=="" (
    echo.
    echo No batch file selected. Exiting.
    pause
    exit /b 1
)

echo.
echo ===========================================================
echo Aforix batch file
echo %BATCH_FILE%
echo ===========================================================
echo.

echo [1/3] Checking batch...
aforix batch check -b "%BATCH_FILE%"
if errorlevel 1 goto failed

echo.
echo [2/3] Execution plan...
aforix batch plan -b "%BATCH_FILE%"
if errorlevel 1 goto failed

echo.
echo [3/3] Running batch...
aforix batch run -b "%BATCH_FILE%"
if errorlevel 1 goto failed

echo.
echo ===========================================================
echo Batch finished successfully.
echo Check runs\batch for manifest.json.
echo ===========================================================
pause
exit /b 0

:failed
echo.
echo ===========================================================
echo Batch failed.
echo Review the messages above and check runs\batch if a manifest was created.
echo ===========================================================
pause
exit /b 1