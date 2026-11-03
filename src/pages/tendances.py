"""Page Tendances : analyses nationales de l'évolution des licences sportives."""

from dash import Dash, Input, Output, dcc, html
import pandas as pd
import plotly.graph_objects as go

from src.utils import couleurs
from src.utils.tendances import (
    ANNEES, SEUIL_LICENCES, effet_covid, evolution_sports,
    sports_comparables, sports_par_defaut, variations,
)

BLEU = couleurs.BLEU_MARINE
VERT = couleurs.POSITIF
ROUGE = couleurs.NEGATIF


def _message(texte: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(text=texte, showarrow=False)
    figure.update_layout(height=390, margin={"l": 20, "r": 20, "t": 15, "b": 20})
    return figure


def creer_variations(debut: int, fin: int) -> go.Figure:
    """Top 8 progressions et top 8 reculs en pourcentage."""
    if debut >= fin:
        return _message("Choisissez une année de début antérieure à l'année de fin.")
    valeurs = variations(debut, fin)
    hausses = valeurs.loc[valeurs["variation"] > 0].head(8)
    baisses = valeurs.loc[valeurs["variation"] < 0].tail(8)
    selection = ( pd.concat([hausses, baisses])
                 .drop_duplicates("sport").sort_values("variation"))
    if selection.empty:
        return _message("Aucun sport comparable avec le seuil retenu.")
    fig = go.Figure(go.Bar(
        x=selection["variation"], y=selection["sport"], orientation="h",
        marker_color=[VERT if x >= 0 else ROUGE for x in selection["variation"]],
        customdata=selection[["licences_debut", "licences_fin"]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>Variation : %{x:+.1f} %"
                       "<br>Début : %{customdata[0]:,.0f} licences"
                       "<br>Fin : %{customdata[1]:,.0f} licences<extra></extra>"),
    ))
    fig.update_layout(height=max(420, len(selection) * 29 + 105),
                      xaxis_title="Variation des licences (%)", yaxis_title=None,
                      margin={"l": 165, "r": 30, "t": 10, "b": 50},
                      plot_bgcolor=couleurs.BLANC, showlegend=False)
    fig.update_xaxes(zeroline=True, zerolinecolor=couleurs.BLEU_MARINE, ticksuffix=" %")
    return fig


def creer_covid() -> go.Figure:
    """Évolutions de grands sports sur les périodes 2019-2021 et 2021-2023."""
    donnees = effet_covid()
    if donnees.empty:
        return _message("Données insuffisantes pour les trois années de comparaison.")
    fig = go.Figure()
    for colonne, nom, couleur in [
        ("variation_2019_2021", "2019 → 2021", ROUGE),
        ("variation_2021_2023", "2021 → 2023", VERT),
    ]:
        fig.add_trace(go.Bar(
            x=donnees["sport"], y=donnees[colonne], name=nom, marker_color=couleur,
            hovertemplate="<b>%{x}</b><br>" + nom + " : %{y:+.1f} %<extra></extra>",
        ))
    fig.update_layout(barmode="group", height=430,
                      margin={"l": 65, "r": 20, "t": 30, "b": 115},
                      yaxis_title="Variation des licences (%)",
                      xaxis_title=None, plot_bgcolor=couleurs.BLANC)
    fig.update_xaxes(tickangle=-35)
    fig.update_yaxes(ticksuffix=" %", zeroline=True, zerolinecolor=couleurs.BLEU_MARINE)
    return fig


def creer_comparaison(sports: list[str]) -> go.Figure:
    """Courbes de licences annuelles pour 2 à 5 sports."""
    if not 2 <= len(sports) <= 5:
        return _message("Choisissez entre deux et cinq sports pour afficher les courbes.")
    donnees = evolution_sports(sports)
    fig = go.Figure()
    for sport in sports:
        courbe = donnees.loc[donnees["sport"] == sport].sort_values("annee")
        if not courbe.empty:
            # Insérer des NaN pour ne pas relier des années non renseignées.
            serie = courbe.set_index("annee")["licences"].reindex(ANNEES)
            fig.add_trace(go.Scatter(
                x=list(ANNEES), y=serie, mode="lines+markers",
                name=sport, connectgaps=False,
                hovertemplate="%{x} : %{y:,.0f} licences<extra>" + sport + "</extra>",
            ))
    fig.update_layout(height=420, xaxis_title="Année", yaxis_title="Nombre de licences",
                      margin={"l": 70, "r": 20, "t": 20, "b": 55}, plot_bgcolor=couleurs.BLANC,
                      colorway=couleurs.SERIES)
    fig.update_xaxes(tickmode="array", tickvals=list(ANNEES))
    return fig


def creer_page() -> html.Div:
    """Présentation de la page Tendances et ses trois visualisations."""
    options = [{"label": str(annee), "value": annee} for annee in ANNEES]
    sports = sports_comparables()
    return html.Div([
        html.H2("Tendances des pratiques sportives"),
        html.P("Comment les licences des fédérations unisports ont-elles évolué en France de 2012 à 2023 ?"),
        html.H3("Les sports qui progressent ou reculent"),
        html.Div([
            html.Div([html.Label("Année de départ"),
                      dcc.Dropdown(id="tendances-debut", options=options, value=2012,
                                   clearable=False)], style={"width": "180px"}),
            html.Div([html.Label("Année d'arrivée"),
                      dcc.Dropdown(id="tendances-fin", options=options, value=2023,
                                   clearable=False)], style={"width": "180px"}),
        ], style={"display": "flex", "gap": "18px", "flexWrap": "wrap"}),
        dcc.Graph(id="tendances-variations", figure=creer_variations(2012, 2023)),
        html.P(f"Seuls les sports avec au moins {SEUIL_LICENCES:,} licences à l'année de départ "
               f"et présents aux deux dates sont comparés.".replace(",", " "),
               style={"fontSize": "13px", "color": couleurs.BLEU_MARINE}),
        html.H3("L'effet du Covid : baisse et reprise"),
        dcc.Graph(id="tendances-covid", figure=creer_covid()),
        html.P("Variations 2019 → 2021 puis 2021 → 2023, pour les grandes disciplines suivies "
               "aux trois dates. Ce graphique ne mesure pas à lui seul l'effet causal du Covid.",
               style={"fontSize": "13px", "color": couleurs.BLEU_MARINE}),
        html.H3("Comparer l'évolution de plusieurs sports"),
        html.Label("Choisir de 2 à 5 sports"),
        dcc.Dropdown(id="tendances-sports",
                     options=[{"label": sport, "value": sport} for sport in sports],
                     value=sports_par_defaut(), multi=True, searchable=True,
                     placeholder="Sélectionner des sports..."),
        dcc.Graph(id="tendances-comparaison"),
        html.P("Les points absents ne sont pas interprétés comme zéro licence. "
               "Attention : certaines fédérations ne sont pas renseignées sur toute la période "
               "(notamment en 2012).",
               style={"fontSize": "13px", "color": couleurs.BLEU_MARINE}),
    ], style={"maxWidth": "1250px", "margin": "auto", "lineHeight": "1.5"})


def enregistrer_callbacks(app: Dash) -> None:
    """Enregistre les interactions spécifiques à la page Tendances."""
    @app.callback(Output("tendances-variations", "figure"),
                  Input("tendances-debut", "value"), Input("tendances-fin", "value"))
    def actualiser_variations(debut: int, fin: int) -> go.Figure:
        return creer_variations(debut, fin)

    @app.callback(Output("tendances-comparaison", "figure"),
                  Input("tendances-sports", "value"))
    def actualiser_comparaison(sports: list[str] | None) -> go.Figure:
        return creer_comparaison(sports or [])
