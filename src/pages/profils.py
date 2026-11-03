"""Page nationale : répartition des licences sportives par sexe et âge."""

from dash import Dash, Input, Output, dcc, html
import pandas as pd
import plotly.graph_objects as go

from src.utils.indicateurs import LIBELLES_AGE
from src.utils.profils import (
    SEUIL_EFFECTIF, licences_par_tranche_age, parts_femmes,
    repartition_ages,
)

BLEU = "#002E85"
ROSE = "#cf5088"
VERT = "#16805c"
ROUGE = "#ba4545"
ANNEES = list(range(2012, 2024))


def _vide(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False)
    fig.update_layout(height=360, margin={"l": 25, "r": 25, "t": 15, "b": 25})
    return fig


def graphique_parts_femmes(annee: int) -> go.Figure:
    """Sports les plus féminins et masculins, en part des licences renseignées."""
    donnees = parts_femmes(annee)
    hauts = donnees.head(8)
    bas = donnees.tail(8)
    affiches = pd.concat([hauts, bas]).drop_duplicates("sport").sort_values("part_femmes")
    if affiches.empty:
        return _vide("Aucun sport ne satisfait le seuil de licences renseignées.")
    fig = go.Figure(go.Bar(
        x=affiches["part_femmes"], y=affiches["sport"], orientation="h",
        marker_color=[ROSE if value >= 50 else BLEU for value in affiches["part_femmes"]],
        customdata=affiches[["femmes", "hommes"]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>Femmes : %{x:.1f} %"
                       "<br>Licences féminines : %{customdata[0]:,.0f}"
                       "<br>Licences masculines : %{customdata[1]:,.0f}<extra></extra>"),
    ))
    fig.update_layout(height=max(440, len(affiches) * 30 + 90),
                      margin={"l": 165, "r": 25, "t": 10, "b": 45},
                      xaxis_title="Part des femmes parmi les licences renseignées (%)",
                      yaxis_title=None, plot_bgcolor="white", showlegend=False)
    fig.update_xaxes(range=[0, 100], ticksuffix=" %")
    fig.add_vline(x=50, line_dash="dash", line_color="#6b7280")
    return fig


def graphique_chaleur(annee: int) -> go.Figure:
    """Répartition par âge (%) des principales disciplines."""
    donnees = repartition_ages(annee)
    if donnees.empty:
        return _vide("Aucune distribution par âge disponible.")
    matrice = donnees.pivot(index="sport", columns="tranche", values="pourcentage")
    ordre = (donnees.groupby("sport")["licences"].sum()
             .sort_values(ascending=False).index.tolist())
    matrice = matrice.reindex(index=ordre, columns=LIBELLES_AGE)
    effectifs = donnees.pivot(index="sport", columns="tranche", values="licences")
    effectifs = effectifs.reindex(index=ordre, columns=LIBELLES_AGE)
    fig = go.Figure(go.Heatmap(
        z=matrice.to_numpy(), x=LIBELLES_AGE, y=matrice.index.tolist(),
        customdata=effectifs.to_numpy(),
        colorscale="Blues", colorbar={"title": "%"},
        hovertemplate=("<b>%{y}</b><br>%{x} : %{z:.1f} %"
                       "<br>%{customdata:,.0f} licences<extra></extra>"),
    ))
    fig.update_layout(height=max(460, len(ordre) * 28 + 95),
                      margin={"l": 150, "r": 35, "t": 20, "b": 80},
                      xaxis_title="Tranche d'âge", yaxis_title="Sport")
    fig.update_yaxes(autorange="reversed")
    return fig


def graphique_tranches_age(annee: int) -> go.Figure:
    """Classe les tranches d'âge selon leur nombre de licences renseignées."""
    donnees = licences_par_tranche_age(annee)
    if donnees["licences"].sum() == 0:
        return _vide("Aucune licence avec âge renseigné pour cette année.")

    # Plus forte valeur en haut ; les étiquettes restent lisibles.
    donnees = donnees.sort_values("licences", ascending=True)
    maximum = donnees["licences"].max()
    couleurs = [VERT if valeur == maximum else BLEU for valeur in donnees["licences"]]
    fig = go.Figure(go.Bar(
        x=donnees["licences"], y=donnees["tranche"], orientation="h",
        marker_color=couleurs, text=donnees["licences"],
        texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False,
        customdata=donnees[["femmes", "hommes"]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>Licences : %{x:,.0f}"
                       "<br>Femmes : %{customdata[0]:,.0f}"
                       "<br>Hommes : %{customdata[1]:,.0f}<extra></extra>"),
    ))
    fig.update_layout(
        height=450, margin={"l": 110, "r": 110, "t": 15, "b": 55},
        xaxis_title="Nombre de licences (sexe et âge renseignés)",
        yaxis_title=None, showlegend=False, plot_bgcolor="white",
    )
    fig.update_xaxes(rangemode="tozero", showgrid=True, gridcolor="#e5e7eb")
    return fig


def creer_page() -> html.Div:
    """Construit la page Profils et ses trois graphiques."""
    options_annees = [{"label": str(annee), "value": annee} for annee in ANNEES]
    return html.Div([
        html.H2("Qui fait du sport ?"),
        html.P("Les licences des fédérations unisports, analysées selon le sexe et l'âge, "
               "pour la France entière."),
        html.Div([
            html.Label("Année d'analyse"),
            dcc.Dropdown(id="profils-annee", options=options_annees, value=2023,
                         clearable=False),
        ], style={"maxWidth": "220px", "marginBottom": "22px"}),
        html.H3("Les sports les plus féminins et les plus masculins"),
        dcc.Graph(id="profils-parts", figure=graphique_parts_femmes(2023)),
        html.P(f"Comparaison limitée aux sports ayant au moins {SEUIL_EFFECTIF:,} "
               "licences avec sexe et âge renseignés pour l'année choisie. "
               "Une part féminine de 50 % est indiquée par le trait pointillé."
               .replace(",", " "), style={"color": "#555", "fontSize": "13px"}),
        html.H3("À quel âge pratique-t-on chaque sport ?"),
        dcc.Graph(id="profils-chaleur", figure=graphique_chaleur(2023)),
        html.P("Chaque case indique le pourcentage des licences renseignées de ce sport "
               "appartenant à la tranche d'âge, et non le nombre brut. "
               "Les quinze disciplines les plus représentées sont affichées.",
               style={"color": "#555", "fontSize": "13px"}),
        html.H3("Quelle tranche d'âge compte le plus de licences ?"),
        dcc.Graph(id="profils-tranches-age", figure=graphique_tranches_age(2023)),
        html.P("Classement national des licences dont l'âge et le sexe sont renseignés. "
               "Les tranches d'âge n'ont pas toutes la même largeur (5, 10 ou 15 ans, "
               "et 75 ans et plus) : un effectif élevé ne signifie donc pas "
               "que les habitants de cette tranche pratiquent proportionnellement plus. "
               "Une licence ne correspond pas forcément à une personne unique.",
               style={"color": "#555", "fontSize": "13px"}),
    ], style={"maxWidth": "1250px", "margin": "auto", "lineHeight": "1.5"})


def enregistrer_callbacks(app: Dash) -> None:
    """Branche les filtres aux graphiques de la page Profils."""
    @app.callback(Output("profils-parts", "figure"), Input("profils-annee", "value"))
    def actualiser_parts(annee: int) -> go.Figure:
        return graphique_parts_femmes(annee)

    @app.callback(Output("profils-chaleur", "figure"), Input("profils-annee", "value"))
    def actualiser_chaleur(annee: int) -> go.Figure:
        return graphique_chaleur(annee)

    @app.callback(Output("profils-tranches-age", "figure"), Input("profils-annee", "value"))
    def actualiser_tranches_age(annee: int) -> go.Figure:
        return graphique_tranches_age(annee)
