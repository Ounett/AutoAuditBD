@echo off
setlocal
cd /d "%~dp0"

where psql >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se encontro psql en PATH.
    echo Instala PostgreSQL 18 para Windows y agrega su carpeta bin al PATH.
    echo Ubicacion habitual: C:\Program Files\PostgreSQL\18\bin
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        where python >nul 2>&1
        if errorlevel 1 (
            echo ERROR: Se necesita Python 3.11 o posterior.
            exit /b 1
        )
        python -m venv .venv
    )
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        exit /b 1
    )
    set "PYTHON=.venv\Scripts\python.exe"
)

"%PYTHON%" -c "import flask, psycopg, dotenv" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias de la interfaz web...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

echo [INFO] Iniciando AutoAudit en Windows...
"%PYTHON%" scripts\arrancar.py
exit /b %errorlevel%
