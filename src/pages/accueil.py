"""Page d'accueil : carte des sports dominants et classement par région."""

from dash import Dash, Input, Output, State, ctx, dcc, html
import plotly.graph_objects as go

import config
from src.components.carte import (
    creer_carte, creer_carte_departements, creer_carte_communes, creer_carte_taux,
    noms_regions, noms_departements, contours_communes_departement,
)
from src.components.classement import creer_classement
from src.components.evolution import creer_evolution
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
                                    "de ses départements. À droite, l'évolution du nombre de licences de "
                                    "la zone choisie ; en dessous, le classement de ses 10 premiers sports."),
                            html.Li("Cliquez sur un département pour voir ses communes, puis sur une commune pour son classement."),
                            html.Li("Utilisez « Retour » pour remonter un niveau."),
                            html.Li("Le premier affichage d'une année ou des communes d'un département "
                                    "peut prendre jusqu'à une minute : les données se chargent puis "
                                    "restent en mémoire, les clics suivants sont rapides."),
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
                            html.Label("Sport à analyser"),
                            dcc.Dropdown(
                                id="sport-analyse",
                                options=[{"label": "Tous les sports", "value": ""}]
                                        + options_sports,
                                value="",
                                searchable=True,
                                clearable=False,
                            ),
                        ],
                        style={"flex": 1, "minWidth": "230px"},
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

            dcc.Store(id="departement-selectionne", data=None),
            dcc.Store(id="commune-selectionnee", data=None),

            # Carte à gauche, évolution du nombre de licences à droite
            html.Div(
                [
                    html.Div(
                        [
                            html.Button(
                                "← Retour",
                                id="bouton-retour",
                                n_clicks=0,
                                style={"marginBottom": "10px"},
                            ),
                            dcc.Loading(
                                dcc.Graph(
                                    id="carte-sports",
                                    config={
                                        "displaylogo": False,
                                        "responsive": True,
                                    },
                                    style={"width": "100%"},
                                ),
                                type="circle",
                            ),
                        ],
                        style={
                            "flex": "1.15 1 0",
                            "minWidth": "420px",
                        },
                    ),

                    html.Div(
                        [
                            html.H3("Évolution du nombre de licences"),

                            html.P(
                                id="nom-zone-evolution",
                                children="France entière",
                            ),
                            html.P(
                                id="note-evolution",
                                style={"fontSize": "13px", "color": "#6b7280"},
                            ),

                            dcc.Loading(
                                dcc.Graph(
                                    id="evolution-licences",
                                    config={"displaylogo": False},
                                    style={"width": "100%"},
                                ),
                                type="circle",
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

            # Classement des sports, sous la carte
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
                style={"marginTop": "30px"},
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

    def zone_selectionnee(region: str | None, departement: str | None,
                          commune: str | None) -> tuple[str, str | None, str]:
        """Niveau, code et nom de la zone la plus précise sélectionnée."""
        if commune:
            zones = contours_communes_departement(departement)
            noms = {str(z["properties"]["code"]): z["properties"].get("nom", commune)
                    for z in zones["features"]}
            return "commune", commune, noms.get(commune, commune)
        if departement:
            return "departement", departement, noms_departements(region).get(departement, departement)
        if region:
            return "region", region, regions.get(region, region)
        return "france", None, "France entière"


    @app.callback(
        Output("carte-sports", "figure"),
        Input("filtre-annee", "value"),
        Input("sports-exclus", "value"),
        Input("sport-analyse", "value"),
        Input("region-selectionnee", "data"),
        Input("departement-selectionne", "data"),
    )
    def actualiser_carte(annee: int, exclusions: list[str], sport: str,
                         code_region: str | None, code_departement: str | None):
        """Carte dominante par défaut, dégradé de rouge pour un sport choisi."""
        if sport:
            if code_departement:
                return creer_carte_taux(annee, sport, "commune",
                                       code_departement=code_departement)
            if code_region:
                return creer_carte_taux(annee, sport, "departement",
                                       code_region=code_region)
            return creer_carte_taux(annee, sport, "region")
        if code_departement:
            return creer_carte_communes(annee, code_departement, exclusions)
        if code_region:
            return creer_carte_departements(annee, code_region, exclusions)
        return creer_carte(annee, exclusions)

    @app.callback(
        Output("region-selectionnee", "data"),
        Output("departement-selectionne", "data"),
        Output("commune-selectionnee", "data"),
        Input("carte-sports", "clickData"),
        Input("bouton-retour", "n_clicks"),
        State("region-selectionnee", "data"),
        State("departement-selectionne", "data"),
        State("commune-selectionnee", "data"),
        prevent_initial_call=True,
    )
    def naviguer(clic: dict | None, _retours: int,
                 region: str | None, departement: str | None,
                 commune: str | None):
        """Navigue d'un niveau au clic et remonte d'un niveau avec Retour."""
        if ctx.triggered_id == "bouton-retour":
            if commune:
                return region, departement, None
            if departement:
                return region, None, None
            return None, None, None

        if not clic or not clic.get("points"):
            return region, departement, commune
        code = str(clic["points"][0].get("location", ""))
        if departement:
            # Un clic sur une commune sélectionne son classement, sans modifier la carte.
            valides = {str(zone["properties"]["code"])
                       for zone in contours_communes_departement(departement)["features"]}
            if code in valides:
                return region, departement, code
        elif region:
            if code in noms_departements(region):
                return region, code, None
        elif code.zfill(2) in regions:
            return code.zfill(2), None, None
        return region, departement, commune

    @app.callback(
        Output("classement-sports", "figure"),
        Output("nom-region", "children"),
        Input("region-selectionnee", "data"),
        Input("departement-selectionne", "data"),
        Input("commune-selectionnee", "data"),
        Input("filtre-annee", "value"),
        Input("sports-exclus", "value"),
    )
    def actualiser_classement(region: str | None, departement: str | None,
                              commune: str | None, annee: int,
                              exclusions: list[str]):
        """Classement de la commune, du département ou de la région sélectionnée."""
        if not region:
            return go.Figure(), "Cliquez sur une région pour afficher son classement."
        niveau, code, nom = zone_selectionnee(region, departement, commune)
        figure = creer_classement(annee, code, exclusions, niveau=niveau)
        return figure, f"Top 10 — {nom} ({annee})"

    @app.callback(
        Output("evolution-licences", "figure"),
        Output("nom-zone-evolution", "children"),
        Output("note-evolution", "children"),
        Input("region-selectionnee", "data"),
        Input("departement-selectionne", "data"),
        Input("commune-selectionnee", "data"),
        Input("filtre-annee", "value"),
        Input("sports-exclus", "value"),
        Input("sport-analyse", "value"),
    )
    def actualiser_evolution(region: str | None, departement: str | None,
                             commune: str | None, annee: int,
                             exclusions: list[str], sport: str | None):
        """Évolution des licences filtrée par sport et par territoire."""
        niveau, code, nom = zone_selectionnee(region, departement, commune)
        figure = creer_evolution(niveau, code, exclusions, annee, sport=sport or None)
        titre = f"{nom} — {sport}" if sport else f"{nom} — Tous les sports"
        note = (
            "Une année sans barre signifie qu'aucune licence n'est renseignée "
            "pour ce sport et ce territoire cette année-là ; ce n'est pas "
            "nécessairement zéro licence. Les fédérations disponibles peuvent "
            "changer selon les années (notamment en 2012)."
            if sport else ""
        )
        return figure, f"{titre}, de 2012 à 2023", note
