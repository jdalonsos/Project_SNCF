# src/data/transform.py
import pandas as pd
import numpy as np


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
    (sentiment, bookings...) pour éviter de tout laisser dans app/.
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

    rng = np.random.default_rng(42)
    max_late = grouped["late_rate"].max() if grouped["late_rate"].max() > 0 else 1.0
    late_norm = grouped["late_rate"] / max_late

    # sentiment
    base_sentiment = 0.35
    sentiment_raw = base_sentiment - 0.3 * late_norm
    sentiment_lagged = sentiment_raw.copy()
    for i in range(1, len(sentiment_lagged)):
        if rng.random() > 0.6:
            sentiment_lagged[i] = sentiment_raw[i - 1]
    sentiment_final = sentiment_lagged + rng.normal(0, 0.15, size=len(grouped))
    grouped["sentiment_score"] = sentiment_final.clip(-1.0, 1.0)

    # bookings
    base_bookings = 20000
    bookings_raw = base_bookings * (1 - 0.4 * late_norm)
    bookings_lagged = bookings_raw.copy()
    for i in range(2, len(bookings_lagged)):
        weights = rng.dirichlet([3, 4, 3])
        bookings_lagged[i] = (
            weights[0] * bookings_raw[i]
            + weights[1] * bookings_raw[i - 1]
            + weights[2] * bookings_raw[i - 2]
        )
    noise = rng.normal(0, base_bookings * 0.1, size=len(grouped))
    grouped["bookings"] = (bookings_lagged + noise).astype(int).clip(5000, 30000)

    return grouped