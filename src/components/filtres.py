"""Filtres de la carte, placés dans l'en-tête qui reste visible quand on descend."""

from dash import dcc, html

import config
from src.utils import couleurs
from src.utils.indicateurs import LIBELLES_AGE, TRANCHES_AGE, liste_sports_uniques

# Style de la zone des filtres ; le callback de main.py ajoute « display: none » hors de la carte.
STYLE_FILTRES = {
    "display": "flex",
    "gap": "20px",
    "alignItems": "flex-end",
    "flexWrap": "wrap",
    "backgroundColor": couleurs.BLANC,
    "borderBottom": f"1px solid {couleurs.BORDURES}",
    "padding": "10px 30px",
    "fontSize": "14px",
}

# Filtres affichés sur chaque page (une page absente de la liste n'en affiche aucun).
FILTRES_PAR_PAGE = {
    "/carte": ["bloc-annee", "bloc-sport", "bloc-sexe", "bloc-ages", "bloc-exclus"],
    "/profils": ["bloc-annee"],
    "/fetiches": ["bloc-annee", "bloc-sport"],
}
TOUS_LES_FILTRES = ["bloc-annee", "bloc-sport", "bloc-sexe", "bloc-ages", "bloc-exclus"]

# Largeur de chaque bloc de filtre (réutilisée par le callback qui affiche ou cache les blocs).
LARGEURS = {
    "bloc-annee": {"width": "130px", "flexShrink": 0},
    "bloc-sport": {"flex": 1, "minWidth": "200px"},
    "bloc-sexe": {"minWidth": "190px"},
    "bloc-ages": {"flex": 1, "minWidth": "200px"},
    "bloc-exclus": {"flex": 1, "minWidth": "200px"},
}


def creer_filtres() -> html.Div:
    """Année, sport à analyser, sexe, tranches d'âge et sports à exclure."""
    annees = sorted(config.LICENCES)
    options_sports = [{"label": sport, "value": sport} for sport in liste_sports_uniques()["sport"]]

    return html.Div(
        [
            html.Div(
                [
                    html.Label("Année"),
                    dcc.Dropdown(
                        id="filtre-annee",
                        options=[{"label": str(a), "value": a} for a in annees],
                        value=annees[-1],
                        clearable=False,
                    ),
                ],
                id="bloc-annee",
                style=LARGEURS["bloc-annee"],
            ),
            html.Div(
                [
                    html.Label("Sport à analyser"),
                    dcc.Dropdown(
                        id="sport-analyse",
                        options=[{"label": "Tous les sports", "value": ""}] + options_sports,
                        value="",
                        searchable=True,
                        clearable=False,
                    ),
                ],
                id="bloc-sport",
                style=LARGEURS["bloc-sport"],
            ),
            html.Div(
                [
                    html.Label("Sexe"),
                    dcc.RadioItems(
                        id="filtre-sexe",
                        options=[{"label": "Tous", "value": "tous"},
                                 {"label": "Femmes", "value": "f"},
                                 {"label": "Hommes", "value": "h"}],
                        value="tous",
                        inline=True,
                        labelStyle={"marginRight": "12px"},
                    ),
                ],
                id="bloc-sexe",
                style=LARGEURS["bloc-sexe"],
            ),
            html.Div(
                [
                    html.Label("Tranches d'âge"),
                    dcc.Dropdown(
                        id="filtre-ages",
                        options=[{"label": libelle, "value": code}
                                 for code, libelle in zip(TRANCHES_AGE, LIBELLES_AGE)],
                        value=[],
                        multi=True,
                        searchable=True,
                        placeholder="Tous les âges",
                    ),
                ],
                id="bloc-ages",
                style=LARGEURS["bloc-ages"],
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
                id="bloc-exclus",
                style=LARGEURS["bloc-exclus"],
            ),
        ],
        id="zone-filtres",
        style=STYLE_FILTRES,
    )
