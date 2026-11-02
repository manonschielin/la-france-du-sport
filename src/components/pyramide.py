"""Pyramide des âges des licenciés (histogramme femmes / hommes par tranche d'âge)."""

import plotly.graph_objects as go

from src.utils.indicateurs import pyramide_ages


def creer_pyramide(
    annee: int,
    niveau: str,
    code: str | None,
    sport: str | None,
    exclusions: list[str],
) -> go.Figure:
    """Pyramide des âges des licenciés : hommes à gauche, femmes à droite."""
    donnees = pyramide_ages(annee, niveau, code, sport, exclusions)

    figure = go.Figure()

    if donnees[["femmes", "hommes"]].to_numpy().sum() == 0:
        figure.add_annotation(text="Aucune donnée pour cette sélection", showarrow=False)
        figure.update_layout(height=450)
        return figure

    # Les hommes sont dessinés vers la gauche (valeurs négatives), mais affichés en positif.
    figure.add_trace(
        go.Bar(
            y=donnees["tranche"],
            x=-donnees["hommes"],
            customdata=donnees["hommes"],
            name="Hommes",
            orientation="h",
            marker_color="#60a5fa",
            hovertemplate="<b>%{y}</b><br>Hommes : %{customdata:,.0f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            y=donnees["tranche"],
            x=donnees["femmes"],
            name="Femmes",
            orientation="h",
            marker_color="#f472b6",
            hovertemplate="<b>%{y}</b><br>Femmes : %{x:,.0f}<extra></extra>",
        )
    )

    # Graduations symétriques, affichées sans le signe moins.
    maximum = int(max(donnees["hommes"].max(), donnees["femmes"].max()))
    moitie = maximum // 2
    graduations = [-maximum, -moitie, 0, moitie, maximum]

    figure.update_layout(
        height=450,
        barmode="relative",
        bargap=0.1,
        margin={"l": 90, "r": 20, "t": 25, "b": 50},
        xaxis={
            "title": "Nombre de licences",
            "range": [-maximum * 1.05, maximum * 1.05],
            "tickvals": graduations,
            "ticktext": [f"{abs(valeur):,}".replace(",", " ") for valeur in graduations],
        },
        yaxis={"title": None},
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"size": 12},
    )
    figure.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=True, zerolinecolor="#9ca3af")

    return figure