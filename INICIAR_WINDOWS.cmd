@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0" || goto error
call PREPARAR_WINDOWS.cmd --no-pause
if errorlevel 1 goto error
echo Iniciando CYBER DATA en http://localhost:8501. Detener con Ctrl+C.
".venv\Scripts\python.exe" -m streamlit run app.py
set "CYBER_EXIT=%ERRORLEVEL%"
endlocal & exit /b %CYBER_EXIT%
:error
echo [ERROR] No se pudo preparar o iniciar CYBER DATA. Revisa los mensajes anteriores.
pause
endlocal & exit /b 1
