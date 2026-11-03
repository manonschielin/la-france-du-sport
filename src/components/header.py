"""En-tête commun à toutes les pages."""

from dash import html

from src.utils import couleurs


def creer_header() -> html.Header:
    """Titre du dashboard et phrase de présentation."""
    return html.Header(
        [
            html.H1("La France du sport", style={"margin": "0"}),
            html.P(
                "Les licences sportives en France de 2012 à 2023, de la région à la commune.",
                style={"margin": "4px 0 0 0", "color": couleurs.BLEU_CLAIR},
            ),
        ],
        style={
            "backgroundColor": couleurs.BLEU_MARINE,
            "color": couleurs.BLANC,
            "padding": "20px 30px",
        },
    )