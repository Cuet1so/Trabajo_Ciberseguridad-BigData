@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0" || goto error_carpeta

title Ciberseguridad Big Data - Instalacion y arranque

echo ================================================
echo   CIBERSEGURIDAD BIG DATA - INICIO AUTOMATICO
echo ================================================
echo.

if not exist "app.py" (
    echo [ERROR] No se encuentra app.py en esta carpeta.
    goto error
)

set "REQ=requirements-lock.txt"
if not exist "%REQ%" (
    if exist "requirements.txt" (
        set "REQ=requirements.txt"
    ) else (
        echo [ERROR] No se encuentra requirements-lock.txt ni requirements.txt.
        goto error
    )
)

echo [1/4] Comprobando Python 3.12...
if not exist ".venv\Scripts\python.exe" (
    call :crear_entorno
    if errorlevel 1 goto error
) else (
    ".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] El entorno .venv existente no utiliza Python 3.12.
        echo Renombra la carpeta .venv como copia de seguridad y vuelve a ejecutar este archivo.
        goto error
    )
    echo [OK] Entorno virtual Python 3.12 encontrado.
)

echo.
echo [2/4] Comprobando pip...
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m ensurepip --upgrade
    if errorlevel 1 goto error
)

echo.
echo [3/4] Instalando dependencias de %REQ%...
".venv\Scripts\python.exe" -m pip install -r "%REQ%"
if errorlevel 1 goto error

echo.
echo [4/4] Comprobando Streamlit...
".venv\Scripts\python.exe" -c "import streamlit" >nul 2>&1
if errorlevel 1 goto error

echo.
echo ================================================
echo   CONFIGURACION COMPLETADA

echo   Iniciando http://localhost:8501
echo   Para detener la aplicacion, pulsa Ctrl+C.
echo ================================================
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
set "EXITCODE=%ERRORLEVEL%"
endlocal & exit /b %EXITCODE%

:crear_entorno
call :buscar_python
if not defined PY312 (
    echo [INFO] No se ha encontrado Python 3.12.
    echo [INFO] Intentando instalarlo con winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] winget no esta disponible en este equipo.
        echo Instala Python 3.12 desde https://www.python.org/downloads/
        exit /b 1
    )
    winget install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements --silent
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar Python 3.12 con winget.
        echo Comprueba la conexion a Internet y los permisos de Windows.
        exit /b 1
    )
    rem Se buscan rutas directamente: winget puede actualizar PATH solo en terminales nuevas.
    call :buscar_python
    if not defined PY312 (
        echo [ERROR] Python se ha instalado, pero no se encuentra en esta sesion.
        echo Cierra y vuelve a abrir VSCode; despues ejecuta este archivo de nuevo.
        exit /b 1
    )
)

echo [OK] Python 3.12: %PY312%
echo [INFO] Creando entorno virtual .venv...
"%PY312%" -m venv ".venv"
if errorlevel 1 (
    echo [ERROR] No se ha podido crear el entorno virtual.
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" exit /b 1
exit /b 0

:buscar_python
set "PY312="
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PY312=%%P"
if defined PY312 exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    exit /b 0
)
if exist "%ProgramFiles%\Python312\python.exe" (
    set "PY312=%ProgramFiles%\Python312\python.exe"
    exit /b 0
)
exit /b 0

:error_carpeta
echo [ERROR] No se pudo abrir la carpeta del proyecto.
:error
echo.
echo La preparacion o el inicio no se han completado.
echo Revisa los mensajes anteriores.
pause
endlocal & exit /b 1
