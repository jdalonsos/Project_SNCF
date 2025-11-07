from __future__ import annotations

import base64
from pathlib import Path
import sys

# ✨ make "src/" importable no matter where Streamlit runs from
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

from src.data.collect_api import (
    telecharger_donnees_sncf,
    get_gares_coordinates,
    trouver_coordonnees,
)
from src.data.transform import enrichir_base, generer_metrics_synthetiques


def get_base64_image(image_path: str) -> Optional[str]:
    """Return a base64-encoded PNG or None if the file doesn't exist."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


def main() -> None:
    st.set_page_config(
        page_title="Dashboard Retards SNCF",
        layout="wide",
    )

    # Load data once per session using Streamlit cache.  If the API
    # cannot be reached, this will return an empty DataFrame.
    @st.cache_data(show_spinner=False)
    def load_data() -> pd.DataFrame:
        df = telecharger_donnees_sncf(nb_annees=5)
        return enrichir_base(df)

    df = load_data()

    # If no data is available, inform the user and abort further UI.
    if df.empty:
        st.error(
            "❌ Impossible de charger les données depuis l'API SNCF. "
            "Vérifiez votre connexion réseau ou réessayez plus tard."
        )
        return

    # Attempt to display a logo if present.  Users can place a file
    # called ``LogoSNCF.png`` in the project root to customise the
    # header.  Otherwise, omit the image gracefully.
    logo_base64 = get_base64_image("LogoSNCF.png")
    title_html = "<h1 style='margin-bottom:0;'>Analyse de la régularité des trains SNCF</h1>"
    if logo_base64:
        title_html = (
            f"<h1 style='display:flex; align-items:center; gap:12px; margin-bottom:0;'>"
            f"<img src='data:image/png;base64,{logo_base64}' width='120'>"
            f"Analyse de la régularité des trains SNCF"
            "</h1>"
        )
    st.markdown(title_html, unsafe_allow_html=True)

    # Sidebar: filters for year range, service, origin and destination.
    with st.sidebar:
        st.header("Filtres")

        # Year range slider
        years = sorted(df["Year"].dropna().unique())
        year_min, year_max = int(min(years)), int(max(years))
        year_range = st.slider(
            "Années", min_value=year_min, max_value=year_max,
            value=(year_min, year_max), step=1
        )

        # Filter dataframe by selected years
        df_filtre = df[df["Year"].between(year_range[0], year_range[1])].copy()

        # Service filter
        services = ["Tous"] + sorted(df_filtre["service"].dropna().unique())
        selected_service = st.selectbox("Type de service", services, index=0)
        if selected_service != "Tous":
            df_filtre = df_filtre[df_filtre["service"] == selected_service]

        # Origin filter
        origins = ["Toutes"] + sorted(df_filtre["gare_depart"].dropna().unique())
        selected_origin = st.selectbox(
            "Gare de départ", origins, index=0, help="Toutes les gares ou une spécifique"
        )
        if selected_origin != "Toutes":
            df_filtre = df_filtre[df_filtre["gare_depart"] == selected_origin]

        # Destination filter (update based on origin)
        destinations = ["Toutes"] + sorted(df_filtre["gare_arrivee"].dropna().unique())
        selected_destination = st.selectbox(
            "Gare d'arrivée", destinations, index=0
        )
        if selected_destination != "Toutes":
            df_filtre = df_filtre[df_filtre["gare_arrivee"] == selected_destination]

        # Cache the filtered result in session state for reuse
        st.session_state.df_filtre = df_filtre

    # If no records match the filters, warn and return early.
    if df_filtre.empty:
        st.warning("Aucune donnée disponible avec les filtres sélectionnés.")
        return

    # Compute high-level KPIs
    total_trains = int(df_filtre["nb_train_prevu"].sum())
    total_cancellations = int(df_filtre["nb_annulation"].sum())
    total_late = int(df_filtre["nb_train_retard_arrivee"].sum())
    avg_delay = float(df_filtre["retard_moyen_tous_trains_arrivee"].mean())

    # Display KPIs
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Trains prévus", f"{total_trains:,}".replace(",", " "))
    kpi_cols[1].metric(
        "Annulations", f"{total_cancellations:,}".replace(",", " "),
        help="Total des trains annulés sur la période sélectionnée"
    )
    kpi_cols[2].metric(
        "Retards", f"{total_late:,}".replace(",", " "),
        help="Nombre total de trains arrivés en retard"
    )
    kpi_cols[3].metric(
        "Retard moyen (min)", f"{avg_delay:.1f}",
        help="Moyenne des minutes de retard à l'arrivée"
    )

    st.markdown("---")

    # Generate synthetic metrics for time series visualisation
    df_metrics = generer_metrics_synthetiques(df_filtre)
    if df_metrics.empty:
        st.info(
            "Pas suffisamment de données pour générer des séries temporelles."
        )
    else:
        # Multi-axis line chart for delay rate, sentiment and bookings
        fig = go.Figure()

        # Delay rate series
        fig.add_trace(
            go.Scatter(
                x=df_metrics["Date"],
                y=df_metrics["late_rate"],
                name="Taux de retard (%)",
                mode="lines",
                line=dict(color="#e74c3c"),
                yaxis="y1",
            )
        )
        # Sentiment series
        fig.add_trace(
            go.Scatter(
                x=df_metrics["Date"],
                y=df_metrics["sentiment_score"],
                name="Sentiment (−1 à 1)",
                mode="lines",
                line=dict(color="#27ae60"),
                yaxis="y2",
            )
        )
        # Bookings series
        fig.add_trace(
            go.Scatter(
                x=df_metrics["Date"],
                y=df_metrics["bookings"],
                name="Réservations",
                mode="lines",
                line=dict(color="#3498db"),
                yaxis="y3",
            )
        )
        # Layout with three y-axes
        fig.update_layout(
            height=500,
            hovermode="x unified",
            xaxis=dict(title="Date"),

            # Y1 = retard
            yaxis=dict(
                title=dict(text="Taux de retard (%)", font=dict(color="#e74c3c")),
                tickfont=dict(color="#e74c3c"),
            ),

            # Y2 = sentiment (droite)
            yaxis2=dict(
                title=dict(text="Sentiment (−1 à 1)", font=dict(color="#27ae60")),
                tickfont=dict(color="#27ae60"),
                overlaying="y",
                side="right",
            ),

            # Y3 = réservations (droite aussi) ⬅️ IMPORTANT: pas de 1.05 ici
            yaxis3=dict(
                title=dict(text="Réservations", font=dict(color="#3498db")),
                tickfont=dict(color="#3498db"),
                overlaying="y",
                side="right",
                # soit on enlève complètement, soit on met un truc valable:
                position=0.98,   # 👈 <= 1, donc ton Plotly l’accepte
                anchor="free",
            ),

            legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
            margin=dict(l=60, r=120, t=40, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Geographic visualisation of delays by departure station
    st.header("Où se concentrent les retards sur le réseau ?")

    # Compute delay rate per departure station
    agg = (
        df_filtre.groupby("gare_depart")
        .agg(
            nb_train_prevu=("nb_train_prevu", "sum"),
            nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
        )
        .reset_index()
    )
    agg["taux_retard"] = (
        agg["nb_train_retard_arrivee"] / agg["nb_train_prevu"] * 100
    ).fillna(0)

    # Attach coordinates
    coords = get_gares_coordinates()
    agg["coords"] = agg["gare_depart"].apply(
        lambda x: trouver_coordonnees(x, coords)
    )
    agg = agg.dropna(subset=["coords"]).copy()

    if agg.empty:
        st.info("Aucune donnée de géolocalisation disponible pour les gares sélectionnées.")
        return

    # Initialise map centred on France
    lats = [lat for lat, _ in agg["coords"]]
    lons = [lon for _, lon in agg["coords"]]
    centre_lat = sum(lats) / len(lats)
    centre_lon = sum(lons) / len(lons)
    m = folium.Map(location=[centre_lat, centre_lon], zoom_start=6)

    # Colour scale thresholds
    for _, row in agg.iterrows():
        lat, lon = row["coords"]
        taux = row["taux_retard"]
        if taux < 20:
            color = "#4CAF50"  # green
        elif taux < 50:
            color = "#FFC107"  # orange
        else:
            color = "#F44336"  # red
        folium.CircleMarker(
            location=[lat, lon],
            radius=5 + (row["nb_train_prevu"] / agg["nb_train_prevu"].max()) * 15,
            popup=(
                f"<b>{row['gare_depart']}</b><br>"
                f"Taux de retard: {taux:.1f}%<br>"
                f"Trains prévus: {int(row['nb_train_prevu'])}"
            ),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.85,
            weight=1,
        ).add_to(m)

    # Display the folium map in Streamlit
    st_folium(m, height=600, use_container_width=True)


if __name__ == "__main__":
    main()
