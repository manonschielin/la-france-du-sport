"""Distribution des taux de licences sportives par commune (histogramme national)."""

from dash import Dash, Input, Output, dcc, html
import plotly.express as px
import plotly.graph_objects as go

import config
from src.utils import couleurs
from src.utils.distribution import distribution_communes, limiter_distribution


def creer_histogramme(
    annee: int,
    sport: str | None,
    seuil_200: bool,
    affichage: str = "principal",
) -> tuple[go.Figure, str]:
    """Histogramme des taux communaux, avec option de cadrage sur le 99e percentile.

    Le mode principal masque uniquement les taux au-delà du 99e percentile
    dans le graphique ; les observations restent dans les données de référence.
    """
    donnees = distribution_communes(
        annee, sport=sport or None, population_minimum=200 if seuil_200 else 0,
    )
    fig = go.Figure()
    if donnees.empty:
        fig.add_annotation(
            text="Aucune commune avec des données exploitables pour cette sélection.",
            showarrow=False,
        )
        fig.update_layout(height=560, paper_bgcolor=couleurs.BLANC)
        return fig, "Aucune observation disponible pour calculer une distribution."

    donnees_affichees, percentile_99, nb_extremes = limiter_distribution(
        donnees, affichage,
    )

    fig = px.histogram(
        donnees_affichees,
        x="taux",
        nbins=35,
        labels={"taux": "Licences pour 1 000 habitants"},
        title=("Distribution des communes — "
               + (sport if sport else "Toutes les fédérations unisports")
               + f" ({annee})"),
        color_discrete_sequence=[couleurs.UNE_COULEUR],
    )
    fig.update_traces(
        hovertemplate="Taux : %{x:.1f} licences pour 1 000 habitants"
                      "<br>Communes : %{y}<extra></extra>",
    )
    fig.update_layout(
        height=560,
        bargap=0,
        xaxis_title="Licences pour 1 000 habitants",
        yaxis_title="Nombre de communes",
        paper_bgcolor=couleurs.BLANC,
        plot_bgcolor=couleurs.BLANC,
        margin={"l": 65, "r": 25, "t": 85, "b": 65},
        font={"color": couleurs.BLEU_MARINE},
    )
    fig.update_xaxes(showgrid=False, rangemode="tozero")
    fig.update_yaxes(showgrid=True, gridcolor=couleurs.BORDURES, rangemode="tozero")

    mediane = donnees["taux"].median()
    resume = (
        f"{len(donnees):,} communes analysées ; taux médian : {mediane:.1f} "
        "licences pour 1 000 habitants. "
        f"99e percentile : {percentile_99:.1f} ; maximum : {donnees['taux'].max():.1f}. "
    ).replace(",", " ")
    if affichage == "principal":
        resume += (
            f"{nb_extremes:,} commune(s) au-dessus du 99e percentile "
            "masquée(s) sur le graphique (non supprimée(s) des données)."
        ).replace(",", " ")
    else:
        resume += "Toutes les communes admissibles sont affichées, y compris les valeurs extrêmes."
    return fig, resume


def creer_page() -> html.Div:
    """Affiche la distribution pour l'année et le sport choisis dans les filtres communs."""
    return html.Div(
        [
            html.H2("Répartition des licences sportives"),
            html.P("Comment les communes françaises se répartissent-elles selon leur "
                   "nombre de licences rapporté à la population ?"),
            html.Div(
                [
                    dcc.Checklist(
                        id="distribution-seuil-200",
                        options=[{"label": "Écarter les communes de moins de 200 habitants", "value": "oui"}],
                        value=["oui"],
                        labelStyle={"cursor": "pointer"},
                    ),
                ],
                style={"padding": "12px 0"},
            ),
            html.Div(
                [
                    html.Label("Affichage de l'histogramme"),
                    dcc.RadioItems(
                        id="distribution-affichage",
                        options=[
                            {"label": "Distribution principale (jusqu'au 99e percentile)",
                             "value": "principal"},
                            {"label": "Toutes les communes (valeurs extrêmes incluses)",
                             "value": "complet"},
                        ],
                        value="principal",
                        inline=True,
                        labelStyle={"cursor": "pointer", "marginRight": "24px"},
                    ),
                ],
                style={"padding": "12px 0"},
            ),
            dcc.Loading(
                dcc.Graph(
                    id="distribution-histogramme",
                    config={"displaylogo": False, "responsive": True},
                )
            ),
            html.P(id="distribution-resume", style={"fontWeight": "bold"}),
            html.H3("Comment lire cet histogramme ?"),
            html.P("Chaque commune compte pour une observation. L'axe horizontal indique "
                   "son nombre de licences pour 1 000 habitants ; l'axe vertical indique "
                   "combien de communes se trouvent dans chaque intervalle de taux. "
                   "Les barres sont contiguës car il s'agit d'une distribution quantitative."),
            html.P("Les fédérations scolaires et multisports sont exclues de ce calcul. "
                   "Les communes sans licences renseignées ou sans population valide "
                   "ne sont pas assimilées à zéro. La population utilisée n'est pas "
                   "historique et une personne peut détenir plusieurs licences : "
                   "ce taux ne mesure donc pas le pourcentage de personnes licenciées. "
                   "La vue principale masque seulement à l'écran les observations au-dessus "
                   "du 99e percentile, tout en indiquant leur nombre. Le mode complet "
                   "permet de les retrouver, sans altérer les données.",
                   style={"fontSize": "13px", "color": couleurs.BLEU_MARINE}),
        ],
        style={"maxWidth": "1300px", "margin": "auto", "lineHeight": "1.5"},
    )


def enregistrer_callbacks(app: Dash) -> None:
    """Réagit à l'année, au sport sélectionné et au seuil de population."""
    @app.callback(
        Output("distribution-histogramme", "figure"),
        Output("distribution-resume", "children"),
        Input("filtre-annee", "value"),
        Input("sport-analyse", "value"),
        Input("distribution-seuil-200", "value"),
        Input("distribution-affichage", "value"),
    )
    def actualiser_distribution(
        annee: int | None, sport: str | None,
        seuil: list[str] | None, affichage: str | None,
    ):
        annee = int(annee) if annee is not None else max(config.LICENCES)
        return creer_histogramme(
            annee, sport, bool(seuil and "oui" in seuil), affichage or "principal",
        )
