# src/data/collect_api.py
import requests
import pandas as pd


BASE_URL = "https://ressources.data.sncf.com/api/records/1.0/search/"
DATASET = "regularite-mensuelle-tgv-aqst"


def telecharger_donnees_sncf(nb_annees: int = 5) -> pd.DataFrame:
    """Télécharge les données SNCF et garde seulement les nb_annees dernières."""
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

    df = pd.DataFrame(all_data)
    df["Date"] = pd.to_datetime(df["date"], format="%Y-%m", errors="coerce")

    date_max = df["Date"].max()
    date_min = date_max - pd.DateOffset(years=nb_annees)
    return df[df["Date"] >= date_min].copy()


def get_gares_coordinates() -> dict:
    """Dico de coords"""
    return {
        "AIX EN PROVENCE TGV": (43.4556, 5.3173),
        "ANGERS SAINT LAUD": (47.4643, -0.5569),
        "ANGOULEME": (45.6489, 0.1584),
        "ANNECY": (45.9136, 6.1267),
        "ARRAS": (50.2892, 2.7806),
        "AVIGNON TGV": (43.9219, 4.7861),
        "BARCELONA": (41.3793, 2.1403),
        "BELFORT MONTBELIARD TGV": (47.5858, 6.9008),
        "BELLEGARDE (AIN)": (46.1078, 5.8283),
        "BELLEGARDE": (46.1078, 5.8283),
        "BESANCON FRANCHE COMTE TGV": (47.3078, 5.9545),
        "BORDEAUX ST JEAN": (44.8263, -0.5567),
        "BORDEAUX SAINT JEAN": (44.8263, -0.5567),
        "BREST": (48.3889, -4.4742),
        "CHAMBERY CHALLES LES EAUX": (45.5614, 5.9806),
        "CHAMPAGNE ARDENNE TGV": (49.2294, 4.0486),
        "CHARLES DE GAULLE": (49.0097, 2.5479),
        "DIJON VILLE": (47.3239, 5.0272),
        "DOUAI": (50.2759, 3.0794),
        "DUNKERQUE": (51.0344, 2.3768),
        "FRANCFORT": (50.1070, 8.6632),
        "FRANKFURT": (50.1070, 8.6632),
        "FREJUS SAINT RAPHAEL": (43.4258, 6.7678),
        "GENEVE": (46.2104, 6.1423),
        "GENEVA": (46.2104, 6.1423),
        "GRENOBLE": (45.1906, 5.7147),
        "HAUTE PICARDIE": (49.8647, 2.8378),
        "ITALIE": (45.4642, 9.1900),
        "ITALY": (45.4642, 9.1900),
        "LA ROCHELLE VILLE": (46.1533, -1.1456),
        "LAVAL": (48.0311, -0.7728),
        "LAUSANNE": (46.5167, 6.6292),
        "LE CREUSOT MONTCEAU MONTCHANIN": (46.7453, 4.4156),
        "LE CREUSOT TGV": (46.7453, 4.4156),
        "LE MANS": (48.0067, 0.1936),
        "LILLE FLANDRES": (50.6367, 3.0708),
        "LILLE EUROPE": (50.6392, 3.0756),
        "LIMOGES BENEDICTINS": (45.8358, 1.2692),
        "LORRAINE TGV": (48.9472, 6.2069),
        "LYON PART DIEU": (45.7606, 4.8594),
        "LYON PERRACHE": (45.7494, 4.8267),
        "MACON LOCHE TGV": (46.3100, 4.7811),
        "MACON LOCHE": (46.3100, 4.7811),
        "MARSEILLE SAINT CHARLES": (43.3028, 5.3808),
        "MARSEILLE ST CHARLES": (43.3028, 5.3808),
        "MARNE LA VALLEE": (48.8706, 2.7819),
        "MARNE LA VALLEE CHESSY": (48.8706, 2.7819),
        "MASSY TGV": (48.7278, 2.2692),
        "MEUSE TGV": (48.9761, 5.2722),
        "METZ VILLE": (49.1094, 6.1769),
        "MONTPELLIER SAINT ROCH": (43.6050, 3.8808),
        "MULHOUSE VILLE": (47.7422, 7.3425),
        "MULHOUSE": (47.7422, 7.3425),
        "NANCY VILLE": (48.6889, 6.1742),
        "NANTES": (47.2169, -1.5414),
        "NARBONNE": (43.1844, 3.0350),
        "NICE VILLE": (43.7042, 7.2619),
        "NIMES": (43.8361, 4.3594),
        "PARIS AUSTERLITZ": (48.8428, 2.3656),
        "PARIS BERCY": (48.8397, 2.3825),
        "PARIS EST": (48.8767, 2.3589),
        "PARIS GARE DE LYON": (48.8442, 2.3739),
        "PARIS LYON": (48.8442, 2.3739),
        "PARIS MONTPARNASSE": (48.8403, 2.3186),
        "PARIS NORD": (48.8808, 2.3553),
        "PARIS ST LAZARE": (48.8761, 2.3250),
        "PERPIGNAN": (42.6981, 2.8956),
        "POITIERS": (46.5806, 0.3406),
        "QUIMPER": (47.9972, -4.0975),
        "REIMS": (49.2586, 4.0247),
        "RENNES": (48.1031, -1.6722),
        "SAINT ETIENNE CHATEAUCREUX": (45.4400, 4.3903),
        "SAINT MALO": (48.6486, -2.0286),
        "ST MALO": (48.6486, -2.0286),
        "SAINT PIERRE DES CORPS": (47.3881, 0.7286),
        "ST PIERRE DES CORPS": (47.3881, 0.7286),
        "SALON DE PROVENCE": (43.6403, 5.0981),
        "STRASBOURG": (48.5847, 7.7350),
        "STUTTGART": (48.7840, 9.1820),
        "TOULON": (43.1258, 5.9306),
        "TOULOUSE MATABIAU": (43.6106, 1.4536),
        "TOURCOING": (50.7242, 3.1614),
        "TOURS": (47.3897, 0.6942),
        "VALENCE TGV": (44.9739, 4.9700),
        "VALENCE ALIXAN TGV": (44.9739, 4.9700),
        "VANNES": (47.6583, -2.7606),
        "VENDOME VILLIERS SUR LOIR TGV": (47.7889, 1.0661),
        "ZURICH": (47.3769, 8.5417),
    }


def trouver_coordonnees(nom_gare: str, gares_coords: dict | None = None):
    if gares_coords is None:
        gares_coords = get_gares_coordinates()

    if not nom_gare:
        return None

    nom = str(nom_gare).upper().strip()

    if nom in gares_coords:
        return gares_coords[nom]

    if f"GARE DE {nom}" in gares_coords:
        return gares_coords[f"GARE DE {nom}"]

    if nom.startswith("GARE DE "):
        nom_sans = nom.replace("GARE DE ", "")
        if nom_sans in gares_coords:
            return gares_coords[nom_sans]

    nom_norm = nom.replace("-", " ").replace("  ", " ")
    if nom_norm in gares_coords:
        return gares_coords[nom_norm]

    for gare_ref, coords in gares_coords.items():
        if nom in gare_ref or gare_ref in nom:
            return coords

    return None
