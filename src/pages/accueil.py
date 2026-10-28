"""Page d'accueil : carte des sports dominants et classement par région."""

from dash import Dash, Input, Output, State, dcc, html
import plotly.graph_objects as go

import config
from src.components.carte import creer_carte, noms_regions
from src.components.classement import creer_classement
from src.utils.indicateurs import liste_sports_uniques


def creer_page() -> html.Div:
    """Construit la mise en page (filtres, carte, classement)."""
    annees = sorted(config.LICENCES)
    sports = liste_sports_uniques()

    options_sports = [
        {
            "label": sport,
            "value": sport,
        }
        for sport in sports["sport"]
    ]

    return html.Div(
        [
            html.H1("La France du sport"),

            html.P(
                "Explorez les pratiques sportives selon les régions."
            ),

            # Filtres
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Année"),
                            dcc.Dropdown(
                                id="filtre-annee",
                                options=[
                                    {"label": str(a), "value": a}
                                    for a in annees
                                ],
                                value=annees[-1],
                                clearable=False,
                            ),
                        ],
                        style={
                            "width": "180px",
                            "flexShrink": 0,
                        },
                    ),

                    html.Div(
                        [
                            html.Label("Sports à exclure"),
                            dcc.Dropdown(
                                id="sports-exclus",
                                options=options_sports,
                                value=[],
                                multi=True,
                                searchable=True,
                                clearable=True,
                                placeholder="Rechercher des sports...",
                            ),
                        ],
                        style={
                            "flex": 1,
                            "minWidth": "250px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "25px",
                    "alignItems": "flex-end",
                    "marginBottom": "30px",
                    "flexWrap": "wrap",
                },
            ),

            # Région sélectionnée, conservée entre les filtres
            dcc.Store(
                id="region-selectionnee",
                data=None,
            ),

            # Carte + classement
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(
                                id="carte-sports",
                                config={
                                    "displaylogo": False,
                                    "responsive": True,
                                },
                                style={"width": "100%"},
                            ),
                        ],
                        style={
                            "flex": "1.15 1 0",
                            "minWidth": "420px",
                        },
                    ),

                    html.Div(
                        [
                            html.H3("Classement des sports"),

                            html.P(
                                id="nom-region",
                                children="Cliquez sur une région.",
                            ),

                            dcc.Graph(
                                id="classement-sports",
                                config={"displaylogo": False},
                                style={"width": "100%"},
                            ),
                        ],
                        style={
                            "flex": "1 1 0",
                            "minWidth": "430px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "25px",
                    "alignItems": "flex-start",
                    "flexWrap": "wrap",
                },
            ),
        ],
        style={
            "maxWidth": "1600px",
            "margin": "auto",
            "padding": "30px",
            "fontFamily": "Arial, sans-serif",
        },
    )


def enregistrer_callbacks(app: Dash) -> None:
    """Relie les filtres et la carte aux graphiques de la page."""
    regions = noms_regions()

    @app.callback(
        Output("carte-sports", "figure"),
        Input("filtre-annee", "value"),
        Input("sports-exclus", "value"),
    )
    def actualiser_carte(
        annee: int,
        exclusions: list[str],
    ):
        """Actualise les couleurs des régions."""
        return creer_carte(annee, exclusions)

    @app.callback(
        Output("region-selectionnee", "data"),
        Input("carte-sports", "clickData"),
        State("region-selectionnee", "data"),
    )
    def memoriser_region(clic: dict | None, region_actuelle: str | None):
        """Mémorise le code de la région cliquée."""
        if not clic or not clic.get("points"):
            return region_actuelle

        code = str(clic["points"][0]["location"]).zfill(2)

        if code not in regions:
            return region_actuelle

        return code

    @app.callback(
        Output("classement-sports", "figure"),
        Output("nom-region", "children"),
        Input("region-selectionnee", "data"),
        Input("filtre-annee", "value"),
        Input("sports-exclus", "value"),
    )
    def actualiser_classement(
        code_region: str | None,
        annee: int,
        exclusions: list[str],
    ):
        """Actualise le classement de la région choisie."""

        if not code_region:
            return (
                go.Figure(),
                "Cliquez sur une région de la carte pour voir son classement.",
            )

        nom = regions.get(code_region, code_region)

        figure = creer_classement(
            annee,
            code_region,
            exclusions,
        )

        return figure, f"Top 10 — {nom} ({annee})"