"""En-tête commun à toutes les pages."""

from dash import html


def creer_header() -> html.Header:
    """Titre du dashboard et phrase de présentation."""
    return html.Header(
        [
            html.H1("La France du sport", style={"margin": "0"}),
            html.P(
                "Les licences sportives en France de 2012 à 2023, de la région à la commune.",
                style={"margin": "4px 0 0 0", "color": "#e0e7ff"},
            ),
        ],
        style={
            "backgroundColor": "#002E85",
            "color": "white",
            "padding": "20px 30px",
        },
    )