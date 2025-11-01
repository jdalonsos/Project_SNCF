
python3 -m venv .venv
source .venv/Scripts/activate
pip install --upgrade pip
pip install poetry

poetry init --no-interaction \
    --name "$P" \
    --description "Streamlit dashboard pour SNCF retards" \
    --author "Amel et Juan" \
    --python "^3.10"

poetry add streamlit pandas matplotlib seaborn plotly requests scikit-learn