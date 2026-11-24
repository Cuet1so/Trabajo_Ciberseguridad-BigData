@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ciberseguridad Big Data - Inicio automatico
call "%~dp0PREPARAR_WINDOWS.cmd" --no-pause
if errorlevel 1 (
    echo [ERROR] No se puede iniciar hasta completar la preparacion.
    pause
    endlocal & exit /b 1
)
echo.
echo [OK] Iniciando el dashboard Streamlit...
echo Presiona Ctrl+C para detenerlo.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
set "RESULT=%ERRORLEVEL%"
endlocal & exit /b %RESULT%
