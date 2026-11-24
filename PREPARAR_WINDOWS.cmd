@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0" || goto error

title Ciberseguridad Big Data - Preparacion del entorno

echo =====================================================
echo  BIG DATA - PREPARACION AUTOMATICA PARA WINDOWS
echo =====================================================
echo.

if not exist "app.py" (
    echo [ERROR] Falta app.py. Copia este archivo a la raiz del proyecto.
    goto error
)
if not exist "requirements.txt" (
    echo [ERROR] Falta requirements.txt.
    goto error
)

echo [1/4] Comprobando Python 3.12...
if not exist ".venv\Scripts\python.exe" (
    call :crear_entorno
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 (
    echo [ERROR] El entorno .venv no usa Python 3.12.
    echo Renombra ese entorno antes de preparar uno nuevo.
    goto error
)
".venv\Scripts\python.exe" --version

echo.
echo [2/4] Verificando pip...
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m ensurepip --upgrade
    if errorlevel 1 goto error
)

echo.
echo [3/4] Instalando dependencias de requirements.txt...
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 (
    echo [ERROR] La instalacion de dependencias ha fallado.
    goto error
)

echo.
echo [4/4] Verificando Streamlit, UMAP y K-means...
".venv\Scripts\python.exe" -c "import streamlit, umap, sklearn, pandas, plotly; print('Dependencias comprobadas.')"
if errorlevel 1 goto error

echo.
echo =====================================================
echo    CONFIGURACION COMPLETADA CORRECTAMENTE
echo =====================================================
echo.
echo Solo falta iniciar el dashboard desde esta carpeta:
echo.
echo    .\.venv\Scripts\python.exe -m streamlit run app.py
echo.
echo Dashboard: http://localhost:8501
echo.
if /I "%~1"=="--no-pause" (endlocal & exit /b 0)
pause
endlocal & exit /b 0

:crear_entorno
call :detectar_python
if not defined PY312 (
    echo [INFO] Python 3.12 no encontrado. Instalando con winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] No esta disponible winget en este Windows.
        echo Instala Python 3.12 desde https://www.python.org/downloads/
        exit /b 1
    )
    winget install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements --silent
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar Python. Comprueba los permisos y la conexion.
        exit /b 1
    )
    call :detectar_python
    if not defined PY312 (
        echo [ERROR] Se instalo Python, pero esta terminal no consigue localizarlo.
        echo Reinicia VSCode y vuelve a ejecutar este preparador.
        exit /b 1
    )
)
echo [INFO] Creando entorno con %PY312% ...
"%PY312%" -m venv ".venv"
if errorlevel 1 exit /b 1
if not exist ".venv\Scripts\python.exe" exit /b 1
exit /b 0

:detectar_python
set "PY312="
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PY312=%%P"
if defined PY312 exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PY312 exit /b 0
if exist "%ProgramFiles%\Python312\python.exe" set "PY312=%ProgramFiles%\Python312\python.exe"
exit /b 0

:error
echo.
echo [ERROR] La preparacion no se ha completado. Revisa los mensajes anteriores.
if /I "%~1"=="--no-pause" (endlocal & exit /b 1)
pause
endlocal & exit /b 1
