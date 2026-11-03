"""Graphique du classement des sports d'une région."""

import plotly.graph_objects as go

from src.utils import couleurs
from src.utils.indicateurs import (
    classement_region, classement_departement, classement_commune,
)


def creer_classement(
    annee: int,
    code_region: str,
    exclusions: list[str],
    niveau: str = "region",
    sexe: str = "tous", tranches: list[str] | None = None,
) -> go.Figure:
    """Crée le graphique des dix premières fédérations."""

    calculs = {"region": classement_region,
               "departement": classement_departement,
               "commune": classement_commune}
    classement = calculs[niveau](annee, code_region, exclusions, sexe, tranches)

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
            marker_color=couleurs.UNE_COULEUR,
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
        plot_bgcolor=couleurs.BLANC,
        paper_bgcolor=couleurs.BLANC,
        font={"size": 12},
        bargap=0.3,
    )

    figure.update_yaxes(
        automargin=True,
        tickfont={"size": 11},
    )

    figure.update_xaxes(
        showgrid=True,
        gridcolor=couleurs.BORDURES,
        rangemode="tozero",
    )

    return figure