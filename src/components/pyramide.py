"""Pyramide des âges des licenciés (histogramme femmes / hommes par tranche d'âge)."""

import plotly.graph_objects as go

from src.utils import couleurs
from src.utils.indicateurs import pyramide_ages, TRANCHES_AGE


def creer_pyramide(
    annee: int,
    niveau: str,
    code: str | None,
    sport: str | None,
    exclusions: list[str],
    sexe: str = "tous", tranches: list[str] | None = None,
) -> go.Figure:
    """Pyramide des âges des licenciés : hommes à gauche, femmes à droite."""
    donnees = pyramide_ages(annee, niveau, code, sport, exclusions, sexe, tranches)

    figure = go.Figure()

    colonnes_visibles = ["femmes"] if sexe == "f" else ["hommes"] if sexe == "h" else ["femmes", "hommes"]
    if donnees[colonnes_visibles].to_numpy().sum() == 0:
        figure.add_annotation(text="Aucune donnée pour cette sélection", showarrow=False)
        figure.update_layout(height=450)
        return figure

    # Les hommes sont dessinés vers la gauche (valeurs négatives), mais affichés en positif.
    selection = set(tranches or [])
    etiquettes = dict(zip(
        TRANCHES_AGE,
        donnees["tranche"],
    ))
    mises_en_avant = {etiquettes[t] for t in selection}
    couleurs_hommes = [couleurs.CATEGORIE_1 if not selection or t in mises_en_avant else couleurs.GRIS_CLAIR
                       for t in donnees["tranche"]]
    couleurs_femmes = [couleurs.CATEGORIE_2 if not selection or t in mises_en_avant else couleurs.GRIS_CLAIR
                       for t in donnees["tranche"]]
    if sexe in ("tous", "h"):
        figure.add_trace(go.Bar(
            y=donnees["tranche"],
            x=-donnees["hommes"],
            customdata=donnees["hommes"],
            name="Hommes",
            orientation="h",
            marker_color=couleurs_hommes,
            hovertemplate="<b>%{y}</b><br>Hommes : %{customdata:,.0f}<extra></extra>",
        ))
    if sexe in ("tous", "f"):
        figure.add_trace(go.Bar(
            y=donnees["tranche"],
            x=donnees["femmes"],
            name="Femmes",
            orientation="h",
            marker_color=couleurs_femmes,
            hovertemplate="<b>%{y}</b><br>Femmes : %{x:,.0f}<extra></extra>",
        ))

    # Graduations symétriques, affichées sans le signe moins.
    maximum = int(max(donnees["hommes"].max() if sexe != "f" else 0,
                      donnees["femmes"].max() if sexe != "h" else 0))
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
        plot_bgcolor=couleurs.BLANC,
        paper_bgcolor=couleurs.BLANC,
        font={"size": 12},
    )
    figure.update_xaxes(showgrid=True, gridcolor=couleurs.BORDURES, zeroline=True, zerolinecolor=couleurs.BLEU_MARINE)

    return figure