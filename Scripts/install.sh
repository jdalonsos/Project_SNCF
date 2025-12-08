#!/usr/bin/env bash
set -e

python3 -m venv .venv

# Activate Windows OR Linux venv
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

pip install --upgrade pip
export PIP_DEFAULT_TIMEOUT=600
pip install poetry
# Tell Poetry to use *this* environment (no extra virtualenv)
poetry config virtualenvs.create false --local || true

# Install project dependencies (including streamlit)
poetry install --no-interaction --no-ansi