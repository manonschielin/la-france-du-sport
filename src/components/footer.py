"""Pied de page commun à toutes les pages."""

from dash import html


def creer_footer() -> html.Footer:
    """Sources des données et auteurs du projet."""
    return html.Footer(
        [
            html.P(
                [
                    "Sources : ",
                    html.A(
                        "recensement des licences sportives (INJEP, data.gouv.fr)",
                        href="https://www.data.gouv.fr/datasets/donnees-geocodees-issues-du-recensement-"
                             "des-licences-et-clubs-aupres-des-federations-sportives-agreees-par-le-"
                             "ministere-charge-des-sports",
                        target="_blank",
                    ),
                    " · ",
                    html.A(
                        "API Découpage administratif",
                        href="https://geo.api.gouv.fr/decoupage-administratif",
                        target="_blank",
                    ),
                    " · ",
                    html.A(
                        "contours administratifs (data.gouv.fr)",
                        href="https://www.data.gouv.fr/datasets/contours-administratifs",
                        target="_blank",
                    ),
                ],
                style={"margin": "0 0 4px 0"},
            ),
            html.P("Projet data Python 2 · ESIEE Paris · Manon Schielin et Thomas Quéro · 2026",
                   style={"margin": "0"}),
        ],
        style={
            "marginTop": "40px",
            "padding": "16px 30px",
            "borderTop": "1px solid #e5e7eb",
            "color": "#6b7280",
            "fontSize": "13px",
        },
    )