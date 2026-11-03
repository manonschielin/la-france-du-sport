"""Barre de navigation entre les pages."""

from dash import dcc, html

# Chaque page du dashboard : (adresse, nom affiché). Ajouter une ligne pour une nouvelle page.
PAGES = [
    ("/", "Accueil"),
    ("/carte", "Explorer la carte"),
    ("/tendances", "Tendances"),
]

STYLE_LIEN = {
    "padding": "12px 18px",
    "color": "#002E85",
    "textDecoration": "none",
    "fontWeight": "bold",
}


def creer_navbar() -> html.Nav:
    """Un lien par page, dans l'ordre de la liste PAGES."""
    return html.Nav(
        [dcc.Link(nom, href=adresse, style=STYLE_LIEN) for adresse, nom in PAGES],
        style={
            "display": "flex",
            "flexWrap": "wrap",
            "backgroundColor": "#eef2ff",
            "borderBottom": "1px solid #c7d2fe",
            "padding": "0 12px",
        },
    )