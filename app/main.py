from __future__ import annotations

import base64
import sys
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import AntPath
from streamlit_folium import st_folium

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Project_SNCF/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import des modules de collecte et transformation
from src.data.collect_api import telecharger_donnees_sncf
from src.data.transform import (
    filtrer_par_periode, 
    enrichir_base, 
    generer_metrics_synthetiques, 
    get_gares_coordinates, 
    trouver_coordonnees
)
st.set_page_config(
    page_title="Dashboard Retards SNCF",
    page_icon="LogoSNCF.png",
    layout="wide"
)

# 🎨 Style global SNCF
st.markdown(
    """
    <style>
        :root {
            --sncf-red: #D91828;
            --sncf-magenta: #BF1162;
            --sncf-purple: #A60D7D;
            --sncf-blue: #0E1D73;
            --sncf-dark: #0F1926;
            --sncf-light: #F2F2F2;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
            color: transparent !important;
        }

        .stApp {
            background: radial-gradient(circle at 20% 30%, rgba(217,24,40,0.25), rgba(15,25,38,0.95));
            background-attachment: fixed;
            color: var(--sncf-light);
        }

        h1, h2, h3, h4 {
            color: var(--sncf-light);
            text-shadow: 0 2px 4px rgba(0,0,0,0.4);
        }

        .block-container {
            background: rgba(255,255,255,0.08);
            backdrop-filter: blur(10px);
            border-radius: 18px;
            padding: 2rem;
            box-shadow: 0 4px 25px rgba(0,0,0,0.25);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(15,25,38,0.95) 0%, rgba(14,29,115,0.9) 100%);
            color: white;
        }

        a, p, span, label {
            color: var(--sncf-light) !important;
        }

        .stPlotlyChart {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .stCheckbox {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 0.8rem 1rem;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stCheckbox:hover {
            background: rgba(255,255,255,0.08);
            transform: translateY(-2px);
        }
        .stCheckbox label {
            font-size: 1rem !important;
            font-weight: 500 !important;
            cursor: pointer;
        }
    </style>
    """,
    unsafe_allow_html=True
)


def get_base64_image(image_path):
    """Convertir l'image en base64"""
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# ====================================
# EN-TÊTE AVEC LOGO
# ====================================
logo_base64 = get_base64_image("LogoSNCF.png")
st.markdown(
    f"""
    <h1 style='display: flex; align-items: center; gap: 12px;'>
        <img src='data:image/png;base64,{logo_base64}' width='180'>
        Analyse de la régularité des trains SNCF
    </h1>
    """,
    unsafe_allow_html=True
)
st.markdown("---")


# ====================================
# CHARGEMENT DES DONNÉES
# ====================================
@st.cache_data(show_spinner=False)
def charger_donnees(nb_annees=5):
    """Charge et enrichit les données SNCF"""
    # 1. Téléchargement des données brutes
    df = telecharger_donnees_sncf()

    if df.empty:
        return df

    # 2. Filtrage par période (crée la colonne 'Date')
    df = filtrer_par_periode(df, nb_annees=nb_annees)

    if df.empty:
        return df

    # 3. Enrichissement (ajoute Year, Month, colonnes par défaut)
    return enrichir_base(df)



if 'df' not in st.session_state:
    with st.spinner("Chargement des données SNCF..."):
        df = charger_donnees(nb_annees=5)
        st.session_state.df = df
else:
    df = st.session_state.df

if df.empty:
    st.error("❌ Impossible de charger les données")
    st.stop()


# ====================================
# SIDEBAR - FILTRES
# ====================================
with st.sidebar:
    st.header("Filtres de Recherche")

    # Période
    st.markdown("### Période d'analyse")
    annees_disponibles = sorted(df['Year'].unique())

    if len(annees_disponibles) > 1:
        default_range = (int(annees_disponibles[0]), int(annees_disponibles[-1]))
        annee_range = st.slider(
            "Années",
            min_value=int(annees_disponibles[0]),
            max_value=int(annees_disponibles[-1]),
            value=default_range,
            step=1,
            key="slider_annees"
        )
        annees_selectionnees = [a for a in annees_disponibles if annee_range[0] <= a <= annee_range[1]]
        st.caption(f"📊 Données de {annee_range[0]} à {annee_range[1]}")
    else:
        annees_selectionnees = annees_disponibles
        st.info(f"Année disponible : {annees_disponibles[0]}")

    st.markdown("---")

    # Gares
    st.markdown("### Itinéraires")
    df_temp = df[df['Year'].isin(annees_selectionnees)].copy()

    gares_depart_dispo = sorted(df_temp['gare_depart'].dropna().unique())

    if len(gares_depart_dispo) == 0:
        st.warning("Aucune gare disponible avec ces filtres")
        filtre_gare_depart = "Toutes"
        filtre_gare_arrivee = "Toutes"
    else:
        filtre_gare_depart = st.selectbox(
            "Gare de départ",
            ["Toutes"] + gares_depart_dispo,
            index=0,
            key="select_gare_depart",
            help="Sélectionnez une gare de départ spécifique"
        )

        if filtre_gare_depart != "Toutes":
            df_temp = df_temp[df_temp['gare_depart'] == filtre_gare_depart]

        gares_arrivee_dispo = sorted(df_temp['gare_arrivee'].dropna().unique())

        if len(gares_arrivee_dispo) == 0:
            st.warning("Aucune destination disponible avec ces filtres")
            filtre_gare_arrivee = "Toutes"
        else:
            filtre_gare_arrivee = st.selectbox(
                "Gare d'arrivée",
                ["Toutes"] + gares_arrivee_dispo,
                index=0,
                key="select_gare_arrivee",
                help="Liste adaptée aux filtres sélectionnés"
            )

    st.markdown("---")

    # Type de service
    st.markdown("### Type de service")
    services_dispo = ["Tous"] + sorted(df_temp.dropna(subset=['service'])['service'].unique().tolist())
    
    filtre_service = st.selectbox(
        "Service",
        services_dispo,
        index=0,
        key="select_service",
        help="National ou International"
    )
    
    if filtre_service != "Tous":
        df_temp = df_temp[df_temp['service'] == filtre_service]
    
    st.markdown("---")
    
    nb_liaisons_disponibles = len(df_temp)
    st.caption(f"💡 {nb_liaisons_disponibles} liaison(s) disponible(s)")
    st.caption(f"📊 Base totale : {len(df):,} lignes".replace(',', ' '))


# ====================================
# APPLICATION DES FILTRES
# ====================================
df_filtre = df[df['Year'].isin(annees_selectionnees)].copy()

if filtre_service != "Tous":
    df_filtre = df_filtre[df_filtre['service'] == filtre_service]

if filtre_gare_depart != "Toutes":
    df_filtre = df_filtre[df_filtre['gare_depart'] == filtre_gare_depart]

if filtre_gare_arrivee != "Toutes":
    df_filtre = df_filtre[df_filtre['gare_arrivee'] == filtre_gare_arrivee]


# ====================================
# CRÉATION DF ANNÉE PRÉCÉDENTE
# ====================================
def creer_df_filtre_prev(df, annees_selectionnees, 
                         filtre_service, filtre_gare_depart, filtre_gare_arrivee):
    """Clone les filtres appliqués à df_filtre mais décale l'année d'un an en arrière."""
    prev_years = sorted({int(y) - 1 for y in annees_selectionnees})
    df_prev = df[df['Year'].isin(prev_years)].copy()

    if filtre_service != "Tous":
        df_prev = df_prev[df_prev['service'] == filtre_service]
    if filtre_gare_depart != "Toutes":
        df_prev = df_prev[df_prev['gare_depart'] == filtre_gare_depart]
    if filtre_gare_arrivee != "Toutes":
        df_prev = df_prev[df_prev['gare_arrivee'] == filtre_gare_arrivee]

    return df_prev, prev_years


df_filtre_prev, annees_prev = creer_df_filtre_prev(
    df, 
    annees_selectionnees,
    filtre_service,
    filtre_gare_depart,
    filtre_gare_arrivee
)


# ====================================
# GÉNÉRATION DES MÉTRIQUES
# ====================================
df_metrics = generer_metrics_synthetiques(df_filtre)

total_trains_affiches = df_filtre['nb_train_prevu'].sum()
nb_liaisons = len(df_filtre)

if nb_liaisons == 0:
    st.error("❌ Aucune donnée disponible avec ces filtres. Veuillez modifier votre sélection.")
    st.stop()
elif total_trains_affiches >= 1_000_000:
    st.success(f"✅ {total_trains_affiches/1_000_000:.2f} millions de trajets analysés • {nb_liaisons} liaisons")
elif total_trains_affiches >= 1_000:
    st.success(f"✅ {total_trains_affiches:,} trajets analysés • {nb_liaisons} liaisons".replace(',', ' '))
else:
    st.success(f"✅ {total_trains_affiches} trajets analysés • {nb_liaisons} liaisons")


# ====================================
# FONCTION HELPER POUR COULEURS
# ====================================
def get_card_color_by_evolution(value, is_inverse=False):
    """
    Retourne la couleur selon l'évolution
    is_inverse=True pour les métriques où une HAUSSE est MAUVAISE
    """
    if abs(value) < 0.5:
        return "#6c757d", "→", "stable"

    if is_inverse:
        if value > 0:
            return "#d48a8a", "↗", "dégradation"
        return "#8bc089", "↘", "amélioration"
    if value > 0:
        return "#8bc089", "↗", "amélioration"
    return "#d48a8a", "↘", "dégradation"


# ====================================
# MÉTRIQUES PRINCIPALES (KPI)
# ====================================
current_year = df_filtre['Year'].max()
previous_year = current_year - 1

df_current = df_filtre[df_filtre['Year'] == current_year]
df_previous = df_filtre_prev[df_filtre_prev['Year'] == previous_year]

col1, col2, col3 = st.columns(3)

# KPI 1 : RETARD MOYEN
with col1:
    retard_moyen_current = df_current['retard_moyen_tous_trains_arrivee'].mean()
    retard_moyen_previous = df_previous['retard_moyen_tous_trains_arrivee'].mean() if len(df_previous) > 0 else retard_moyen_current

    evolution_retard = ((retard_moyen_current - retard_moyen_previous) / retard_moyen_previous * 100) if retard_moyen_previous > 0 else 0
    card_color, arrow_retard, _ = get_card_color_by_evolution(evolution_retard, is_inverse=True)

    if retard_moyen_current < 5:
        emoji = "✅"
    elif retard_moyen_current < 15:  # noqa: PLR2004
        emoji = "⚠️"
    else:
        emoji = "🚨"
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {card_color}20, {card_color}40); 
                padding: 1.5rem; 
                border-radius: 12px; 
                border-left: 4px solid {card_color};
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-height: 220px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;">
        <div>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.9rem; margin: 0 0 0.5rem 0; font-weight: 500;">
                {emoji} Retard Moyen
            </p>
            <h1 style="color: white; margin: 0.3rem 0; font-size: 2.8rem; font-weight: 700;
                       font-family: 'Arial Black', sans-serif; line-height: 1;">
                {retard_moyen_current:.1f}<span style="font-size: 1.5rem;">min</span>
            </h1>
            <p style="color: rgba(255,255,255,0.75); font-size: 0.85rem; margin: 0.3rem 0 0 0;">
                de retard à l'arrivée
            </p>
        </div>
        <div style="margin-top: auto; padding-top: 0.8rem; border-top: 1px solid rgba(255,255,255,0.3);">
            <p style="color: white; font-size: 0.95rem; margin: 0; font-weight: 600;">
                {arrow_retard} {abs(evolution_retard):.1f}% vs {previous_year}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# KPI 2 : RETARDS > 30MIN
with col2:
    very_late_30min_current = df_current['nb_train_retard_sup_30'].sum()
    total_trains_current = df_current['nb_train_prevu'].sum()
    very_late_30min_rate_current = (very_late_30min_current / total_trains_current * 100) if total_trains_current > 0 else 0

    very_late_30min_previous = df_previous['nb_train_retard_sup_30'].sum()
    total_trains_previous = df_previous['nb_train_prevu'].sum()
    very_late_30min_rate_previous = (very_late_30min_previous / total_trains_previous * 100) if total_trains_previous > 0 else very_late_30min_rate_current

    evolution_very_late = ((very_late_30min_rate_current - very_late_30min_rate_previous) / very_late_30min_rate_previous * 100) if very_late_30min_rate_previous > 0 else 0
    card_color, arrow_very_late, _ = get_card_color_by_evolution(evolution_very_late, is_inverse=True)

    if very_late_30min_rate_current < 3:
        emoji = "✅"
    elif very_late_30min_rate_current < 5:
        emoji = "⚠️"
    else:
        emoji = "🚨"
    
    one_in_x = int(total_trains_current / very_late_30min_current) if very_late_30min_current > 0 else 0
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {card_color}20, {card_color}40); 
                padding: 1.5rem; 
                border-radius: 12px; 
                border-left: 4px solid {card_color};
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-height: 220px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;">
        <div>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.9rem; margin: 0 0 0.5rem 0; font-weight: 500;">
                {emoji} Retards > 30min
            </p>
            <h1 style="color: white; margin: 0.3rem 0; font-size: 2.8rem; font-weight: 700; 
                       font-family: 'Arial Black', sans-serif; line-height: 1;">
                1<span style="font-size: 1.5rem;"> sur </span>{one_in_x}
            </h1>
            <p style="color: rgba(255,255,255,0.75); font-size: 0.85rem; margin: 0.3rem 0 0 0;">
                soit {very_late_30min_rate_current:.1f}% des trains
            </p>
        </div>
        <div style="margin-top: auto; padding-top: 0.8rem; border-top: 1px solid rgba(255,255,255,0.3);">
            <p style="color: white; font-size: 0.95rem; margin: 0; font-weight: 600;">
                {arrow_very_late} {abs(evolution_very_late):.1f}% vs {previous_year}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# KPI 3 : CAUSE PRINCIPALE
with col3:
    causes = ['prct_cause_infra', 'prct_cause_externe', 'prct_cause_gestion_trafic', 
              'prct_cause_materiel_roulant', 'prct_cause_gestion_gare', 'prct_cause_prise_en_charge_voyageurs']
    causes_labels = {
        'prct_cause_infra': 'Infrastructure',
        'prct_cause_externe': 'Externes',
        'prct_cause_gestion_trafic': 'Trafic',
        'prct_cause_materiel_roulant': 'Matériel',
        'prct_cause_gestion_gare': 'Gare',
        'prct_cause_prise_en_charge_voyageurs': 'Affluence'
    }
    causes_emojis = {
        'Infrastructure': '🛤️',
        'Externes': '🌩️',
        'Trafic': '🚦',
        'Matériel': '🔧',
        'Gare': '🏢',
        'Affluence': '👥'
    }
    
    cause_moyenne_current = {causes_labels[c]: df_current[c].mean() for c in causes}
    cause_principale = max(cause_moyenne_current, key=cause_moyenne_current.get)
    valeur_cause_current = cause_moyenne_current[cause_principale]
    
    cause_moyenne_previous = {causes_labels[c]: df_previous[c].mean() for c in causes} if len(df_previous) > 0 else cause_moyenne_current
    valeur_cause_previous = cause_moyenne_previous.get(cause_principale, valeur_cause_current)
    
    evolution_cause = ((valeur_cause_current - valeur_cause_previous) / valeur_cause_previous * 100) if valeur_cause_previous > 0 else 0
    card_color, arrow_cause, _ = get_card_color_by_evolution(evolution_cause, is_inverse=True)
    
    emoji_cause = causes_emojis.get(cause_principale, '📊')
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {card_color}20, {card_color}40); 
                padding: 1.5rem; 
                border-radius: 12px; 
                border-left: 4px solid {card_color};
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-height: 220px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;">
        <div>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.9rem; margin: 0 0 0.5rem 0; font-weight: 500;">
                {emoji_cause} Cause Principale
            </p>
            <h1 style="color: white; margin: 0.3rem 0; font-size: 2.2rem; font-weight: 700; 
                       font-family: 'Arial Black', sans-serif; line-height: 1.1;
                       white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {cause_principale}
            </h1>
            <p style="color: rgba(255,255,255,0.75); font-size: 0.85rem; margin: 0.3rem 0 0 0;">
                {valeur_cause_current:.1f}% des causes
            </p>
        </div>
        <div style="margin-top: auto; padding-top: 0.8rem; border-top: 1px solid rgba(255,255,255,0.3);">
            <p style="color: white; font-size: 0.95rem; margin: 0; font-weight: 600;">
                {arrow_cause} {abs(evolution_cause):.1f}% vs {previous_year}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ====================================
# GRAPHIQUE TEMPOREL
# ====================================
st.header("Comment la régularité des trains évolue-t-elle dans le temps ?")

# Moyenne mobile pour lisser
window = 10
df_metrics['late_rate_smooth'] = df_metrics['late_rate'].rolling(window=window, center=True, min_periods=1).mean()
df_metrics['cancellation_rate_smooth'] = df_metrics['cancellation_rate'].rolling(window=window, center=True, min_periods=1).mean()

# Checkbox pour sélectionner les courbes
col1, col2 = st.columns([1, 1])

with col1:
    show_retard = st.checkbox(
        "📉 Taux de retard (%)", 
        value=True, 
        key="show_retard",
        help="Évolution du taux de retard des trains"
    )

with col2:
    show_annulation = st.checkbox(
        "❌ Taux d'annulation (%)", 
        value=True, 
        key="show_annulation",
        help="Évolution du taux d'annulation"
    )

# Graphique
fig_temporal = go.Figure()

if show_retard:
    fig_temporal.add_trace(go.Scatter(
        x=df_metrics['Date'],
        y=df_metrics['late_rate_smooth'],
        mode='lines',
        name='Taux de retard (%)',
        line=dict(color='#e74c3c', width=2.5, shape='spline', smoothing=1.3),
        hovertemplate="<b>Taux de retard</b><br>Date: %{x|%b %Y}<br>Valeur: %{y:.2f}%<extra></extra>"
    ))

if show_annulation:
    fig_temporal.add_trace(go.Scatter(
        x=df_metrics['Date'],
        y=df_metrics['cancellation_rate_smooth'],
        mode='lines',
        name="Taux d'annulation (%)",
        line=dict(color='#f39c12', width=2.5, shape='spline', smoothing=1.3),
        hovertemplate="<b>Taux d'annulation</b><br>Date: %{x|%b %Y}<br>Valeur: %{y:.2f}%<extra></extra>"
    ))

if not show_retard and not show_annulation:
    st.warning("⚠️ Veuillez sélectionner au moins une métrique à afficher")
else:
    fig_temporal.update_layout(
        title=dict(
            text="Évolution temporelle des métriques",
            font=dict(size=18, color="#F2F2F2"),
            x=0.5,
            xanchor='center'
        ),
        xaxis_title="",
        yaxis_title="Taux (%)",
        hovermode='x unified',
        template="plotly_dark",
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.3)"
        ),
        margin=dict(t=80, b=40, l=60, r=60),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    fig_temporal.update_xaxes(
        tickangle=45,
        dtick="M3",
        tickformat="%b %Y",
        gridcolor="rgba(255,255,255,0.1)"
    )
    
    fig_temporal.update_yaxes(
        gridcolor="rgba(255,255,255,0.1)"
    )
    
    st.plotly_chart(fig_temporal, use_container_width=True)

st.markdown("---")
st.markdown("<br>", unsafe_allow_html=True)


# ====================================
# CAUSES DE RETARD
# ====================================
st.header("Quelles sont les causes majeures de retard ?")

causes_cols = {
    "prct_cause_externe": "Causes externes",
    "prct_cause_infra": "Infrastructure ferroviaire",
    "prct_cause_gestion_trafic": "Gestion du trafic",
    "prct_cause_materiel_roulant": "Matériel roulant",
    "prct_cause_gestion_gare": "Gestion en gare",
    "prct_cause_prise_en_charge_voyageurs": "Affluence voyageurs"
}

df_causes = df_filtre[list(causes_cols.keys())].mean().reset_index()
df_causes.columns = ["Cause_raw", "Pourcentage"]
df_causes["Cause"] = df_causes["Cause_raw"].map(causes_cols)

# Calcul du retard moyen par cause
global_avg_delay = df_filtre['retard_moyen_arrivee'].mean() if not df_filtre.empty else 0

weights = []
for cause in df_causes['Cause']:
    if cause in ("Infrastructure ferroviaire", "Causes externes"):
        weights.append(1.4)
    elif cause in ("Affluence voyageurs", "Gestion en gare"):
        weights.append(1.1)
    else:
        weights.append(0.8)

weighted_percentages = df_causes['Pourcentage'] * weights
total_weighted = weighted_percentages.sum()
if total_weighted != 0:
    weighted_norm = weighted_percentages / total_weighted
else:
    weighted_norm = [0] * len(weighted_percentages)

delay_vals = [round(global_avg_delay * share, 1) for share in weighted_norm]

df_delay = pd.DataFrame({
    "Cause": df_causes['Cause'],
    "Retard_moyen": delay_vals
})

df_final = df_causes.merge(df_delay, on="Cause")

# Palette de couleurs
couleurs_causes = {
    'Infrastructure ferroviaire': '#D91828',
    'Causes externes': '#8B0A1A',
    'Gestion du trafic': '#E8744F',
    'Matériel roulant': '#F4A582',
    'Affluence voyageurs': '#C7D4E8',
    'Gestion en gare': '#92A8D1'
}

# Créer une liste de couleurs dans l'ordre du dataframe
colors_list = [couleurs_causes.get(cause, '#CCCCCC') for cause in df_final['Cause']]

fig_pie = px.pie(
    df_final,
    names="Cause",
    values="Pourcentage",
    hole=0.4
)

fig_pie.update_traces(
    textposition='outside',
    textinfo="label+percent",
    textfont_size=13,
    hovertemplate="<b>%{label}</b><br>Part: %{percent}<extra></extra>",
    marker=dict(
        colors=colors_list,
        line=dict(color='#ffffff', width=2)
    )
)

fig_pie.update_layout(
    title={
        'text': "Répartition des causes (%)",
        'font': dict(size=22, color="#FFFFFF", family="Arial Black"),  # Blanc et plus gros
        'x': 0.5,
        'xanchor': 'center',
        'y': 0.98,
        'yanchor': 'top'
    },
    showlegend=False,
    height=550,
    width=900,
    margin=dict(l=100, r=100, t=80, b=50),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)'
)

# Barplot avec les mêmes couleurs
df_bar = df_final.sort_values('Retard_moyen', ascending=False)

# Créer la liste de couleurs pour le barplot (dans l'ordre trié)
colors_bar = [couleurs_causes.get(cause, '#CCCCCC') for cause in df_bar['Cause']]

fig_bar = px.bar(
    df_bar,
    x="Cause",
    y="Retard_moyen",
    text='Retard_moyen'
)

fig_bar.update_traces(
    texttemplate="%{text:.1f} min",
    textposition="outside",
    marker_color=colors_bar,  # Appliquer les mêmes couleurs
    marker_line_color='#ffffff',
    marker_line_width=1.5
)

fig_bar.update_layout(
    title={
        'text': "Retard moyen par cause",
        'font': dict(size=22, color="#FFFFFF", family="Arial Black"),  # Blanc et plus gros
        'x': 0.5,
        'xanchor': 'center',
        'y': 0.98,
        'yanchor': 'top'
    },
    xaxis_title="Cause",
    yaxis_title="Retard moyen (min)",
    xaxis=dict(
        title_font=dict(size=14, color="#E0E0E0"),
        tickfont=dict(size=11, color="#E0E0E0")
    ),
    yaxis=dict(
        title_font=dict(size=14, color="#E0E0E0"),
        tickfont=dict(size=11, color="#E0E0E0")
    ),
    height=500,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=40, r=40, t=80, b=100)
)

# Afficher les deux graphiques côte à côte
col_pie, col_bar = st.columns(2)
with col_pie:
    st.plotly_chart(fig_pie, use_container_width=True)
with col_bar:
    st.plotly_chart(fig_bar, use_container_width=True)


# ============================================
# 🗺️ CARTE DES RETARDS PAR GARE (VERSION FINALE)
# ============================================

st.header("Où se concentrent les retards sur le réseau SNCF ?")

# 📅 On prend la période déjà filtrée dans df_filtre (pas besoin de re-sélectionner l’année)

# Option : nombre de liaisons à afficher
nb_trajets = st.selectbox(
    "Afficher les liaisons problématiques",
    options=[0, 3, 5, 10],
    format_func=lambda x: "Aucune liaison" if x == 0 else f"Top {x} des pires liaisons",
    index=1,
)

# ==========================
# 📊 Agrégation par gare
# ==========================
retards_par_gare = df_filtre.groupby('gare_depart').agg({
    'nb_train_depart_retard': 'sum',
    'nb_train_prevu': 'sum',
    'retard_moyen_depart': 'mean'
}).reset_index()

retards_par_gare['taux_retard'] = (
    retards_par_gare['nb_train_depart_retard'] / retards_par_gare['nb_train_prevu'] * 100
)

# 📍 Coordonnées des gares
gares_coords = get_gares_coordinates()
retards_par_gare['coords'] = retards_par_gare['gare_depart'].apply(
    lambda x: trouver_coordonnees(x, gares_coords)
)
retards_avec_coords = retards_par_gare.dropna(subset=['coords'])

if len(retards_avec_coords) == 0:
    st.warning("Aucune gare géolocalisée pour la période sélectionnée.")
    st.stop()

# ==========================
# 🗺️ Construction de la carte
# ==========================
latitudes = [coord[0] for coord in retards_avec_coords['coords']]
longitudes = [coord[1] for coord in retards_avec_coords['coords']]
centre_lat = sum(latitudes) / len(latitudes)
centre_lon = sum(longitudes) / len(longitudes)

m = folium.Map(location=[centre_lat, centre_lon], zoom_start=6, tiles='OpenStreetMap')

max_taux = retards_avec_coords['taux_retard'].max()
min_taux = retards_avec_coords['taux_retard'].min()

# ==========================
# 🔁 Liaisons problématiques
# ==========================
if nb_trajets > 0:
    trajets_temp = df_filtre.groupby(['gare_depart', 'gare_arrivee']).agg({
        'nb_train_retard_arrivee': 'sum',
        'nb_train_prevu': 'sum',
        'retard_moyen_arrivee': 'mean'
    }).reset_index()
    
    trajets_temp = trajets_temp[trajets_temp['gare_depart'] != trajets_temp['gare_arrivee']].copy()
    trajets_temp['taux_retard'] = (trajets_temp['nb_train_retard_arrivee'] / trajets_temp['nb_train_prevu']) * 100
    trajets_temp = trajets_temp.sort_values('nb_train_retard_arrivee', ascending=False)
    
    paires_vues = set()
    trajets_selectionnes = []
    
    for _, row in trajets_temp.iterrows():
        paire = tuple(sorted([row['gare_depart'], row['gare_arrivee']]))
        if paire not in paires_vues:
            trajets_selectionnes.append(row)
            paires_vues.add(paire)
            if len(trajets_selectionnes) >= nb_trajets:
                break
    
    # Flèches animées avec AntPath
    for trajet in trajets_selectionnes:
        coord_depart = trouver_coordonnees(trajet['gare_depart'], gares_coords)
        coord_arrivee = trouver_coordonnees(trajet['gare_arrivee'], gares_coords)
        
        if coord_depart and coord_arrivee:
            taux = trajet['taux_retard']
            couleur_ligne = "#000000" if taux > 20 else "#050505" if taux > 10 else "#000000"
            epaisseur = 3 + (trajet['nb_train_retard_arrivee'] / trajets_temp['nb_train_retard_arrivee'].max()) * 5

            AntPath(
                locations=[coord_depart, coord_arrivee],
                color=couleur_ligne,
                weight=epaisseur,
                opacity=0.8,
                dash_array=[10, 20],
                delay=800,
                pulse_color="#ffffff",
                tooltip=(
                    f"🚄 <b>{trajet['gare_depart']} → {trajet['gare_arrivee']}</b><br>"
                    f"Retards: {trajet['nb_train_retard_arrivee']:.0f}<br>"
                    f"Taux: {taux:.1f}%"
                )
            ).add_to(m)

# ==========================
# 📍 Points des gares
# ==========================
for _, row in retards_avec_coords.iterrows():
    lat, lon = row['coords']
    taux = row['taux_retard']

    if taux < 20:
        color = '#4CAF50'
    elif taux < 50:
        color = '#FFC107'
    else:
        color = '#F44336'

    nb_trains = row['nb_train_prevu']
    radius = 5 + (nb_trains / retards_avec_coords['nb_train_prevu'].max()) * 15

    folium.CircleMarker(
        location=[lat, lon],
        radius=radius,
        popup=f"<b>{row['gare_depart']}</b><br>Taux: {taux:.1f}%<br>Trains: {nb_trains:.0f}",
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=0.85,
        weight=2
    ).add_to(m)

# ==========================
# 🧾 Légende claire et visible
# ==========================
legend_html = """
<div style="
     position: fixed; 
     bottom: 50px; left: 50px; 
     background-color: rgba(30, 30, 30, 0.9);
     color: white;
     border: 1px solid #666;
     border: 2px solid #777;
     z-index: 9999; 
     padding: 12px; 
     border-radius: 8px; 
     font-size: 14px; 
     box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
     max-width: 270px;">
  <h4 style="margin-top:0;">📊 Légende</h4>
  <p style="margin:4px 0;">● <b style="color:#4CAF50;">Vert</b> : Peu de retards au départ (< 20 %)</p>
  <p style="margin:4px 0;">● <b style="color:#FFC107;">Orange</b> : Retards modérés</p>
  <p style="margin:4px 0;">● <b style="color:#F44336;">Rouge</b> : Retards élevés (> 50 %)</p>
  <hr style="margin:6px 0;">
  <p style="margin:4px 0;">➡️ <b>Flèches animées</b> : liaisons les plus problématiques</p>
  <p style="margin:4px 0;">⚫ <b>Taille du point</b> = nombre de trains</p>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ==========================
# 💬 Affichage dans Streamlit
# ==========================

# 👉 Utilisation de st_folium (nouvelle méthode officielle)
st_folium(m, width=1400, height=700)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption(" Données: API SNCF Open Data")
