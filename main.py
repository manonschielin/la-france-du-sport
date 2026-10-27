
"""Point d'entrée du dashboard La France du sport."""

from dash import Dash, Input, Output, State, dcc, html
import plotly.graph_objects as go

import config
from src.components.carte import creer_carte, noms_regions
from src.utils.indicateurs import (
    classement_region,
    liste_sports_uniques,
)


app = Dash(__name__)

annees = sorted(config.LICENCES)
regions = noms_regions()
sports = liste_sports_uniques()

options_sports = [
    {
        "label": sport,
        "value": sport,
    }
    for sport in sports["sport"]
]

def creer_classement(
    annee: int,
    code_region: str,
    exclusions: list[str],
) -> go.Figure:
    """Crée le graphique des dix premières fédérations."""

    classement = classement_region(
        annee,
        code_region,
        exclusions,
    )

    figure = go.Figure()

    if classement.empty:
        figure.add_annotation(
            text="Aucune donnée pour cette sélection",
            showarrow=False,
        )
        figure.update_layout(height=550)
        return figure

    classement = classement.sort_values("licences")
    
    figure.add_trace(
        go.Bar(
            x=classement["licences"],
            y=classement["sport"],
            orientation="h",
            marker_color="#6366f1",
            text=classement["licences"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b>"
                "<br>Licences : %{x:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=550,
        margin={
            "l": 125,
            "r": 70,
            "t": 25,
            "b": 50,
        },
        xaxis_title="Nombre de licences",
        yaxis_title=None,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"size": 12},
        bargap=0.3,
    )

    figure.update_yaxes(
        automargin=True,
        tickfont={"size": 11},
    )

    figure.update_xaxes(
        showgrid=True,
        gridcolor="#e5e7eb",
        rangemode="tozero",
    )

    return figure


app.layout = html.Div(
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


if __name__ == "__main__":
    app.run(debug=True)
