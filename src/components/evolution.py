"""Diagramme en barres du nombre de licences par année."""

import plotly.graph_objects as go

from src.utils.indicateurs import licences_par_annee


def creer_evolution(
    niveau: str,
    code: str | None,
    exclusions: list[str],
    annee_choisie: int,
) -> go.Figure:
    """Licences par année de la zone choisie ; l'année du filtre est mise en avant."""
    donnees = licences_par_annee(niveau, code, exclusions)

    figure = go.Figure()

    if donnees.empty:
        figure.add_annotation(text="Aucune donnée pour cette sélection", showarrow=False)
        figure.update_layout(height=450)
        return figure

    couleurs = ["#6366f1" if annee == annee_choisie else "#c7d2fe" for annee in donnees["annee"]]

    figure.add_trace(
        go.Bar(
            x=donnees["annee"],
            y=donnees["licences"],
            marker_color=couleurs,
            hovertemplate="<b>%{x}</b><br>Licences : %{y:,.0f}<extra></extra>",
        )
    )

    figure.update_layout(
        height=450,
        margin={"l": 70, "r": 20, "t": 25, "b": 50},
        xaxis_title="Année",
        yaxis_title="Nombre de licences",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"size": 12},
        bargap=0.25,
    )
    figure.update_xaxes(tickmode="linear", dtick=1)
    figure.update_yaxes(showgrid=True, gridcolor="#e5e7eb", rangemode="tozero")

    return figure