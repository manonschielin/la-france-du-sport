"""Page d'accueil : carte des sports dominants et classement par région."""

from dash import Dash, Input, Output, State, ctx, dcc, html
import plotly.graph_objects as go

import config
from src.components.carte import creer_carte, creer_carte_departements, noms_regions
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

                        # Mode d'emploi
            html.Div(
                [
                    html.Strong("Comment utiliser la carte :"),
                    html.Ol(
                        [
                            html.Li("Choisissez une année et, si vous le souhaitez, des sports à exclure "
                                    "(par exemple le football, présent partout)."),
                            html.Li("Cliquez sur une région : la carte affiche le sport dominant de chacun "
                                    "de ses départements, et le classement des 10 premiers sports de la "
                                    "région apparaît à droite."),
                            html.Li("Cliquez sur « ← Retour à la France » pour revenir à la carte des régions."),
                        ],
                        style={"margin": "8px 0 0 0", "paddingLeft": "20px"},
                    ),
                ],
                style={
                    "backgroundColor": "#f3f4f6",
                    "borderLeft": "4px solid #6366f1",
                    "padding": "12px 16px",
                    "marginBottom": "25px",
                    "fontSize": "14px",
                },
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
                            html.Button(
                                "← Retour à la France",
                                id="bouton-retour",
                                n_clicks=0,
                                style={"marginBottom": "10px"},
                            ),
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
        Input("region-selectionnee", "data"),
    )
    def actualiser_carte(
        annee: int,
        exclusions: list[str],
        code_region: str | None,
    ):
        """Carte des régions, ou des départements si une région est choisie."""
        if code_region:
            return creer_carte_departements(annee, code_region, exclusions)
        return creer_carte(annee, exclusions)

    @app.callback(
        Output("region-selectionnee", "data"),
        Input("carte-sports", "clickData"),
        Input("bouton-retour", "n_clicks"),
        State("region-selectionnee", "data"),
    )
    def memoriser_region(
        clic: dict | None,
        _clics_retour: int,
        region_actuelle: str | None,
    ):
        """Mémorise la région cliquée, ou revient à la France avec le bouton."""
        if ctx.triggered_id == "bouton-retour":
            return None

        # Sur la carte des départements, un clic ne change pas de région.
        if region_actuelle is not None:
            return region_actuelle

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