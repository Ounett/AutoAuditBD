@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        exit /b 1
    )
)

set "PYTHON=.venv\Scripts\python.exe"
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

where psql >nul 2>&1
if errorlevel 1 (
    echo ERROR: Instala PostgreSQL 18 y agrega psql al PATH antes de continuar.
    exit /b 1
)

echo Instala PostgreSQL 18, inicia su servicio y ejecuta iniciar.bat para preparar la base.
exit /b 0
