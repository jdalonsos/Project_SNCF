# src/data/transform.py
import pandas as pd


def enrichir_base(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute Year, Month et sécurise quelques colonnes."""
    if df.empty:
        return df

    df = df.copy()
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month

    # si certaines colonnes n’existent pas dans une version de l’API
    cols_defaut = [
        "nb_train_prevu",
        "nb_annulation",
        "nb_train_retard_arrivee",
        "retard_moyen_tous_trains_arrivee",
    ]
    for c in cols_defaut:
        if c not in df.columns:
            df[c] = 0

    return df


def generer_metrics_synthetiques(df_filtre: pd.DataFrame) -> pd.DataFrame:
    """
    pour éviter de tout laisser dans app/.
    """
    if df_filtre.empty:
        return df_filtre

    grouped = (
        df_filtre.groupby(["Year", "Month"])
        .agg(
            nb_train_prevu=("nb_train_prevu", "sum"),
            nb_annulation=("nb_annulation", "sum"),
            nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
            retard_moyen=("retard_moyen_tous_trains_arrivee", "mean"),
        )
        .reset_index()
    )

    grouped["Date"] = pd.to_datetime(
        grouped[["Year", "Month"]].assign(day=1)
    )
    grouped["late_rate"] = (
        grouped["nb_train_retard_arrivee"] / grouped["nb_train_prevu"] * 100
    ).fillna(0)
    grouped["cancellation_rate"] = (
        grouped["nb_annulation"] / grouped["nb_train_prevu"] * 100
    ).fillna(0)

    return grouped
