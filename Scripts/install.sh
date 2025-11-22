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
pip install poetry
