#!/usr/bin/env bash
# Preparacion del entorno para Ciberseguridad Big Data.
# Ejecutar desde zsh/bash: bash ./PREPARAR_ENTORNO.sh
set -Eeuo pipefail

cd "$(dirname "$0")"

error() {
    printf '\n[ERROR] %s\n' "$1" >&2
    exit 1
}

printf '\n========================================\n'
printf '  CYBER DATA - PREPARACION\n'
printf '========================================\n\n'

[[ -f "app.py" ]] || error "No encuentro app.py en la carpeta del script."
[[ -f "requirements-lock.txt" ]] || error "No encuentro requirements-lock.txt en la carpeta del script."

printf '[1/3] Comprobando Python 3.12...\n'
# Utilizar el entorno local si ya existe. Si no existe, buscar Python 3.12
# de forma compatible con macOS/Linux y terminales tipo Git Bash de Windows.
VENV_PY=""
if [[ -f ".venv/bin/python" ]]; then
    VENV_PY=".venv/bin/python"
elif [[ -f ".venv/Scripts/python.exe" ]]; then
    VENV_PY=".venv/Scripts/python.exe"
fi

if [[ -z "$VENV_PY" ]]; then
    PY_CMD=()
    if command -v python3.12 >/dev/null 2>&1 && python3.12 -c 'import sys; assert sys.version_info[:2] == (3, 12)' 2>/dev/null; then
        PY_CMD=(python3.12)
    elif command -v python >/dev/null 2>&1 && python -c 'import sys; assert sys.version_info[:2] == (3, 12)' 2>/dev/null; then
        PY_CMD=(python)
    elif command -v py >/dev/null 2>&1 && py -3.12 -c 'import sys; assert sys.version_info[:2] == (3, 12)' 2>/dev/null; then
        PY_CMD=(py -3.12)
    fi

    if (( ${#PY_CMD[@]} == 0 )); then
        error "No se encuentra Python 3.12. Instalalo y vuelve a ejecutar este archivo."
    fi

    printf 'Creando el entorno virtual .venv...\n'
    "${PY_CMD[@]}" -m venv .venv || error "No se pudo crear el entorno virtual."

    if [[ -f ".venv/bin/python" ]]; then
        VENV_PY=".venv/bin/python"
    elif [[ -f ".venv/Scripts/python.exe" ]]; then
        VENV_PY=".venv/Scripts/python.exe"
    else
        error "El entorno virtual se ha creado, pero no encuentro su ejecutable de Python."
    fi
fi

"$VENV_PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' \
    || error "El entorno .venv no utiliza Python 3.12. Renombra ese entorno y vuelve a ejecutar este script."
"$VENV_PY" --version

printf '\n[2/3] Instalando dependencias de requirements-lock.txt...\n'
"$VENV_PY" -m pip install -r requirements-lock.txt \
    || error "No se pudieron instalar las dependencias. Revisa tu conexion o los errores de pip."

printf '\n[3/3] Verificando Streamlit y librerias principales...\n'
"$VENV_PY" -c 'import streamlit, umap, sklearn, pandas, plotly; print("Dependencias verificadas correctamente.")' \
    || error "No se han podido importar Streamlit, UMAP y scikit-learn."

"$VENV_PY" -m pip check || error "Hay dependencias incompatibles. Revisa pip check antes de iniciar."

printf '\n========================================\n'
printf '       CONFIGURACION COMPLETADA\n'
printf '========================================\n'
printf 'El entorno esta listo. Solo falta iniciar el dashboard.\n\n'
printf 'Si tu terminal ya muestra (.venv), ejecuta:\n'
printf '  python -m streamlit run app.py\n\n'
printf 'Si NO tienes el entorno activado, ejecuta:\n'
printf '  %s -m streamlit run app.py\n\n' "$VENV_PY"

printf "\nDashboard: http://localhost:8501 · Detener con Ctrl+C.\n"
