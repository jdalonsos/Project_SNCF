# src/data/collect_api.py
import pandas as pd
import requests

BASE_URL = "https://ressources.data.sncf.com/api/records/1.0/search/"
DATASET = "regularite-mensuelle-tgv-aqst"


def telecharger_donnees_sncf(nb_annees: int = 5) -> pd.DataFrame:
    """Télécharge les données SNCF brutes."""
    params = {
        "dataset": DATASET,
        "rows": 10000,
        "sort": "date",
        "facet": ["service", "gare_depart", "gare_arrivee"],
    }

    all_data = []
    offset = 0

    for _ in range(20):
        params["start"] = offset
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            if offset == 0:
                return pd.DataFrame()
            break

        records = data.get("records", [])
        if not records:
            break

        for rec in records:
            all_data.append(rec["fields"])

        offset += len(records)
        if len(records) < params["rows"]:
            break

    if not all_data:
        return pd.DataFrame()

    return pd.DataFrame(all_data)


