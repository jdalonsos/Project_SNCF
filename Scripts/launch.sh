#!/usr/bin/env bash
set -e

# Go to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

poetry add folium streamlit_folium geopy streamlit

# Activate virtual environment (Windows layout)
source .venv/Scripts/activate

# Run Streamlit app with Poetry
poetry run streamlit run app/main.py