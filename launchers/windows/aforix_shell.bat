@echo off
setlocal

REM ============================================================
REM Aforix Windows shell launcher
REM ============================================================

REM Edit these variables if necessary.
set REPO_DIR=D:\repos\aforix
set CONDA_ENV=aforix
set CONDA_BAT=

REM If conda is not available globally, set CONDA_BAT explicitly, for example:
REM set CONDA_BAT=C:\Users\%USERNAME%\miniconda3\condabin\conda.bat
REM set CONDA_BAT=C:\ProgramData\miniconda3\condabin\conda.bat

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
echo ===========================================================
echo Aforix shell ready
echo Repository: %REPO_DIR%
echo Environment: %CONDA_ENV%
echo ===========================================================
echo.

cmd /k