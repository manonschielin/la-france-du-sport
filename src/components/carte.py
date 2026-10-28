
"""Création de la carte des pratiques sportives."""

import json
from functools import lru_cache

import plotly.express as px
import plotly.graph_objects as go

import config
from src.utils.indicateurs import sport_numero_un, sport_numero_un_departements
from src.utils.referentiel import couleur_sport


CODES_OUTRE_MER = {"01", "02", "03", "04", "06"}


@lru_cache(maxsize=1)
def contours_regions() -> dict:
    """Charge les contours métropolitains une seule fois."""
    chemin = config.DATA_RAW_DIR / "contours_regions.geojson"

    with open(chemin, encoding="utf-8") as fichier:
        contours = json.load(fichier)

    contours["features"] = [
        zone
        for zone in contours["features"]
        if str(zone["properties"]["code"]).zfill(2)
        not in CODES_OUTRE_MER
    ]

    return contours


def noms_regions() -> dict[str, str]:
    """Associe chaque code région à son nom."""
    return {
        str(zone["properties"]["code"]).zfill(2):
        zone["properties"]["nom"]
        for zone in contours_regions()["features"]
    }


def creer_carte(
    annee: int,
    exclusions: list[str] | None = None,
) -> go.Figure:
    """Affiche les fédérations dominantes sur la carte."""

    contours = contours_regions()
    donnees = sport_numero_un(annee, exclusions).copy()

    donnees = donnees.loc[
        ~donnees["code_region"].isin(CODES_OUTRE_MER)
    ]

    donnees["region"] = (
        donnees["code_region"].map(noms_regions())
    )

    # Une couleur fixe pour chaque code fédération.
    donnees["couleur"] = donnees["code_federation"].apply(
        couleur_sport
    )

    if donnees.empty:
        figure = go.Figure()
        figure.add_annotation(
            text="Aucune donnée disponible pour ces filtres",
            showarrow=False,
        )
    else:
        couleurs = dict(
            zip(donnees["sport"], donnees["couleur"])
        )

        figure = px.choropleth(
            donnees,
            geojson=contours,
            locations="code_region",
            featureidkey="properties.code",
            color="sport",
            color_discrete_map=couleurs,
            custom_data=[
                "region",
                "sport",
                "licences",
            ],
        )

        figure.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>Sport dominant : %{customdata[1]}"
                "<br>Licences : %{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
            marker_line_color="white",
            marker_line_width=1,
        )

    figure.update_geos(
        fitbounds=False,
        projection_type="mercator",
        lonaxis_range=[-6, 10],
        lataxis_range=[41, 52],
        visible=False,
    )

    figure.update_layout(
        title=f"Sports dominants par région — {annee}",
        height=650,
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
        legend_title_text="Sport dominant",
        clickmode="event",
        uirevision="carte-france",
    )

    return figure


@lru_cache(maxsize=1)
def contours_departements() -> dict:
    """Charge les contours des départements une seule fois."""
    chemin = config.DATA_RAW_DIR / "contours_departements.geojson"

    with open(chemin, encoding="utf-8") as fichier:
        return json.load(fichier)


def contours_departements_region(code_region: str) -> dict:
    """Garde seulement les départements d'une région."""
    return {
        "type": "FeatureCollection",
        "features": [
            zone
            for zone in contours_departements()["features"]
            if zone["properties"]["region"] == code_region
        ],
    }


def creer_carte_departements(
    annee: int,
    code_region: str,
    exclusions: list[str] | None = None,
) -> go.Figure:
    """Affiche le sport dominant de chaque département d'une région."""

    contours = contours_departements_region(code_region)
    noms = {
        zone["properties"]["code"]: zone["properties"]["nom"]
        for zone in contours["features"]
    }

    donnees = sport_numero_un_departements(annee, list(noms), exclusions).copy()
    donnees["departement"] = donnees["code_departement"].map(noms)

    # Même couleur que sur la carte des régions pour un même sport.
    donnees["couleur"] = donnees["sport"].apply(couleur_sport)

    if donnees.empty:
        figure = go.Figure()
        figure.add_annotation(
            text="Aucune donnée disponible pour ces filtres",
            showarrow=False,
        )
    else:
        couleurs = dict(zip(donnees["sport"], donnees["couleur"]))

        figure = px.choropleth(
            donnees,
            geojson=contours,
            locations="code_departement",
            featureidkey="properties.code",
            color="sport",
            color_discrete_map=couleurs,
            custom_data=[
                "departement",
                "sport",
                "licences",
            ],
        )

        figure.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>Sport dominant : %{customdata[1]}"
                "<br>Licences : %{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
            marker_line_color="white",
            marker_line_width=1,
        )

    # Zoom automatique sur les départements de la région.
    figure.update_geos(
        fitbounds="locations",
        projection_type="mercator",
        visible=False,
    )

    figure.update_layout(
        title=f"Sports dominants par département — {noms_regions().get(code_region, code_region)} ({annee})",
        height=650,
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
        legend_title_text="Sport dominant",
        clickmode="event",
        uirevision=code_region,
    )

    return figure
