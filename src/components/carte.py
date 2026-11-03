
"""Création de la carte des pratiques sportives."""

import json
from functools import lru_cache

import plotly.express as px
import plotly.graph_objects as go

import config
from src.utils.indicateurs import (
    sport_numero_un, sport_numero_un_departements, sport_numero_un_communes,
)
from src.utils import couleurs as palette
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


def creer_carte_taux(annee: int, sport: str, niveau: str,
                     code_region: str | None = None,
                     code_departement: str | None = None,
                     sexe: str = "tous", tranches: list[str] | None = None) -> go.Figure:
    """Carte d'un sport en rouge selon son taux de licences / 1 000 habitants."""
    import pandas as pd
    from src.utils.indicateurs import licences_pour_1000

    if niveau == "region":
        geojson = contours_regions()
        titre_zone = "région"
    elif niveau == "departement":
        if code_region is None:
            raise ValueError("Région requise pour les départements")
        geojson = contours_departements_region(code_region)
        titre_zone = "département"
    elif niveau == "commune":
        if code_departement is None:
            raise ValueError("Département requis pour les communes")
        geojson = contours_communes_departement(code_departement)
        titre_zone = "commune"
    else:
        raise ValueError(f"Échelle inconnue : {niveau}")

    codes = [str(z["properties"]["code"]) for z in geojson["features"]]
    noms = [z["properties"].get("nom", code)
            for z, code in zip(geojson["features"], codes)]
    donnees = licences_pour_1000(annee, sport, niveau, sexe, tranches)
    valeurs = donnees.set_index("code").reindex(codes)
    # Tracé gris couvrant TOUTES les zones (y compris sans licences).
    figure = go.Figure()
    if codes:
        figure.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.code",
            locations=codes, z=[0] * len(codes),
            colorscale=[[0, palette.GRIS_CLAIR], [1, palette.GRIS_CLAIR]],
            showscale=False, marker_line_color=palette.BLANC, marker_line_width=0.6,
            text=noms, name="Sans données", showlegend=False,
            hovertemplate="<b>%{text}</b><br>Taux indisponible<extra></extra>",
        ))
        valides = valeurs["taux"].notna().to_numpy()
        if valides.any():
            codes_valides = [c for c, ok in zip(codes, valides) if ok]
            noms_valides = [n for n, ok in zip(noms, valides) if ok]
            lignes = valeurs.loc[codes_valides]
            figure.add_trace(go.Choropleth(
                geojson=geojson, featureidkey="properties.code",
                locations=codes_valides, z=lignes["taux"].astype(float),
                colorscale=palette.ECHELLE_PLOTLY,
                colorbar={"title": "Licences / 1 000 hab."},
                marker_line_color=palette.BLANC, marker_line_width=0.6,
                text=noms_valides,
                customdata=lignes[["licences", "population"]].to_numpy(),
                hovertemplate=("<b>%{text}</b><br>Taux : %{z:.1f} / 1 000 hab."
                               "<br>Licences : %{customdata[0]:,.0f}"
                               "<br>Population : %{customdata[1]:,.0f}<extra></extra>"),
                name=sport,
            ))
    else:
        figure.add_annotation(text="Aucun contour disponible", showarrow=False)

    options = {"projection_type": "mercator", "visible": False, "bgcolor": palette.FOND_CARTES_GEO}
    if niveau == "region":
        options.update(fitbounds=False, lonaxis_range=[-6, 10],
                       lataxis_range=[41, 52])
    else:
        options["fitbounds"] = "locations" if codes else False
    figure.update_geos(**options)
    figure.update_layout(
        title=f"{sport} — licences pour 1 000 habitants par {titre_zone} ({annee})",
        height=650, paper_bgcolor=palette.FOND_CARTES_GEO, margin={"l": 0, "r": 0, "t": 55, "b": 0},
        clickmode="event", uirevision=f"taux-{niveau}-{code_region}-{code_departement}",
    )
    return figure


def creer_carte(
    annee: int,
    exclusions: list[str] | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> go.Figure:
    """Affiche les fédérations dominantes sur la carte."""

    contours = contours_regions()
    donnees = sport_numero_un(annee, exclusions, sexe, tranches).copy()

    donnees = donnees.loc[
        ~donnees["code_region"].isin(CODES_OUTRE_MER)
    ]

    donnees["region"] = (
        donnees["code_region"].map(noms_regions())
    )

    # Couleur stable par nom de sport (identique aux départements).
    donnees["couleur"] = donnees["sport"].apply(couleur_sport)

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
            marker_line_color=palette.BLANC,
            marker_line_width=1,
        )

    figure.update_geos(
        fitbounds=False,
        projection_type="mercator",
        lonaxis_range=[-6, 10],
        lataxis_range=[41, 52],
        visible=False,
        bgcolor=palette.FOND_CARTES_GEO,
    )

    figure.update_layout(
        title=f"Sports dominants par région — {annee}",
        height=650,
        paper_bgcolor=palette.FOND_CARTES_GEO,
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
    sexe: str = "tous", tranches: list[str] | None = None,
) -> go.Figure:
    """Affiche le sport dominant de chaque département d'une région."""

    contours = contours_departements_region(code_region)
    noms = {
        zone["properties"]["code"]: zone["properties"]["nom"]
        for zone in contours["features"]
    }

    donnees = sport_numero_un_departements(annee, list(noms), exclusions, sexe, tranches).copy()
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
            marker_line_color=palette.BLANC,
            marker_line_width=1,
        )

    # Zoom automatique sur les départements de la région.
    figure.update_geos(
        fitbounds="locations",
        projection_type="mercator",
        visible=False,
        bgcolor=palette.FOND_CARTES_GEO,
    )

    figure.update_layout(
        title=f"Sports dominants par département — {noms_regions().get(code_region, code_region)} ({annee})",
        height=650,
        paper_bgcolor=palette.FOND_CARTES_GEO,
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
        legend_title_text="Sport dominant",
        clickmode="event",
        uirevision=code_region,
    )

    return figure


@lru_cache(maxsize=1)
def _index_contours_communes() -> dict[str, list[dict]]:
    """Indexe les contours communaux par département, sans relecture à chaque clic."""
    chemin = config.DATA_RAW_DIR / "contours_communes.geojson"
    with open(chemin, encoding="utf-8") as fichier:
        contours = json.load(fichier)
    index: dict[str, list[dict]] = {}
    for zone in contours["features"]:
        code = str(zone["properties"]["code"])
        # Les préfixes 97/98 ont un département à trois caractères.
        departement = code[:3] if code.startswith(("97", "98")) else code[:2]
        index.setdefault(departement, []).append(zone)
    return index


def contours_communes_departement(code_departement: str) -> dict:
    """Retourne uniquement les contours du département choisi."""
    return {"type": "FeatureCollection",
            "features": _index_contours_communes().get(str(code_departement), [])}


def noms_departements(code_region: str) -> dict[str, str]:
    """Codes et noms des départements d'une région."""
    contours = contours_departements_region(code_region)
    return {str(z["properties"]["code"]): z["properties"]["nom"]
            for z in contours["features"]}


def creer_carte_communes(annee: int, code_departement: str,
                         exclusions: list[str] | None = None,
                         sexe: str = "tous", tranches: list[str] | None = None) -> go.Figure:
    """Affiche le sport dominant des communes d'un seul département."""
    contours = contours_communes_departement(code_departement)
    noms = {str(z["properties"]["code"]): z["properties"].get("nom", "")
            for z in contours["features"]}
    donnees = sport_numero_un_communes(annee, list(noms), exclusions, sexe, tranches).copy()
    donnees["commune"] = donnees["code_commune"].map(noms)
    figure = go.Figure()
    # Tracé de fond : inclut aussi les communes sans licences et permet leurs clics.
    if noms:
        figure.add_trace(go.Choropleth(
            geojson=contours, featureidkey="properties.code",
            locations=list(noms), z=[0] * len(noms),
            colorscale=[[0, palette.GRIS_CLAIR], [1, palette.GRIS_CLAIR]],
            showscale=False, marker_line_color=palette.BLANC, marker_line_width=0.5,
            text=list(noms.values()),
            hovertemplate="<b>%{text}</b><br>Aucune donnée affichée<extra></extra>",
            name="Communes", showlegend=False,
        ))
    if not donnees.empty:
        couleurs = {sport: couleur_sport(sport) for sport in donnees["sport"].unique()}
        for sport, groupe in donnees.groupby("sport", sort=True):
            figure.add_trace(go.Choropleth(
                geojson=contours, featureidkey="properties.code",
                locations=groupe["code_commune"], z=[1] * len(groupe),
                colorscale=[[0, couleurs[sport]], [1, couleurs[sport]]],
                showscale=False, marker_line_color=palette.BLANC, marker_line_width=0.5,
                name=sport, showlegend=True,
                customdata=groupe[["commune", "licences"]].to_numpy(),
                hovertemplate=("<b>%{customdata[0]}</b><br>Sport dominant : "
                               + sport + "<br>Licences : %{customdata[1]:,.0f}<extra></extra>"),
            ))
    if not noms:
        figure.add_annotation(text="Aucun contour disponible pour ce département",
                              showarrow=False)
    figure.update_geos(fitbounds="locations" if noms else False,
                       projection_type="mercator", visible=False,
                       bgcolor=palette.FOND_CARTES_GEO)
    figure.update_layout(
        title=f"Sports dominants par commune — {code_departement} ({annee})",
        height=650, paper_bgcolor=palette.FOND_CARTES_GEO, margin={"l": 0, "r": 0, "t": 55, "b": 0},
        legend_title_text="Sport dominant", clickmode="event",
        uirevision=f"communes-{code_departement}",
    )
    return figure
