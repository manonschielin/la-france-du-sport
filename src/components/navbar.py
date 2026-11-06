"""Barre de navigation entre les pages."""

from dash import dcc, html

from src.utils import couleurs

# Chaque page du dashboard : (adresse, nom affiché). Ajouter une ligne pour une nouvelle page.
PAGES = [
    ("/", "Accueil"),
    ("/carte", "Explorer la carte"),
    ("/tendances", "Tendances"),
    ("/profils", "Qui fait du sport ?"),
    ("/fetiches", "Répartition des licences"),
]

STYLE_LIEN = {
    "padding": "12px 18px",
    "color": couleurs.BLEU_MARINE,
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
            "backgroundColor": couleurs.BLANC,
            "borderBottom": f"3px solid {couleurs.BLEU_CLAIR}",
            "padding": "0 12px",
        },
    )