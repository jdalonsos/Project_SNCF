#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate Windows OR Linux venv
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

printf "\n==============================================\n"
printf "Streamlit app (open in your browser):\n"
printf "  • http://localhost:8501\n"
printf "  • http://host.docker.internal:8501  (if supported)\n\n"
printf "==============================================\n\n"

poetry run streamlit run app/main.py --server.address 0.0.0.0 --server.port 8501
