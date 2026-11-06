"""Tests du niveau communal, sans accès réseau ni données volumineuses."""

import sqlite3

import pandas as pd
import pytest

import config
from src.components import carte
from src.utils import indicateurs


@pytest.fixture
def environnement(tmp_path, monkeypatch):
    """Petite base comprenant deux communes, deux sports et deux années."""
    db = tmp_path / "sports.db"
    monkeypatch.setattr(config, "DB_PATH", db)
    monkeypatch.setattr(config, "DATA_RAW_DIR", tmp_path)
    indicateurs.donnees_communes.cache_clear()
    carte._index_contours_communes.cache_clear()
    with sqlite3.connect(db) as cn:
        pd.DataFrame([
            (2023, "01001", "01", "100", 10),
            (2023, "01001", "01", "101", 30),
            (2023, "01002", "01", "100", 80),
            (2023, "01002", "01", "101", 5),
            (2023, "01002", "01", "600", 200),
            (2022, "01001", "01", "100", 3),
        ], columns=["annee", "code_commune", "code_departement", "code_federation", "total"]).to_sql(
            "cleaned_licences", cn, index=False)
        pd.DataFrame([
            ("100", "FF de Football", "unisport olympique"),
            ("101", "FF de Tennis", "unisport olympique"),
            ("600", "Sport scolaire", "scolaire et universitaire"),
        ], columns=["code", "nom", "famille"]).to_sql("cleaned_federations", cn, index=False)
    import json
    zones = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"code": code, "nom": name},
         "geometry": {"type": "Polygon", "coordinates": [[
             [lon, 46], [lon + 0.1, 46], [lon + 0.1, 46.1], [lon, 46.1], [lon, 46]
         ]]}}
        for code, name, lon in [
            ("01001", "Commune A", 5.0), ("01002", "Commune B", 5.2),
            ("2A001", "Commune Corse", 8.8)
        ]
    ]}
    (tmp_path / "contours_communes.geojson").write_text(json.dumps(zones), encoding="utf-8")
    yield
    indicateurs.donnees_communes.cache_clear()
    carte._index_contours_communes.cache_clear()


def test_dominante_et_exclusion(environnement):
    donnees = indicateurs.sport_numero_un_communes(2023, ["01001", "01002"])
    assert donnees.set_index("code_commune").loc["01001", "sport"] == "Tennis"
    assert donnees.set_index("code_commune").loc["01002", "sport"] == "Football"
    sans_foot = indicateurs.sport_numero_un_communes(2023, ["01001", "01002"], ["Football"])
    assert sans_foot["sport"].tolist() == ["Tennis", "Tennis"]
    assert indicateurs.classement_commune(2023, "01002", ["Football"])["licences"].sum() == 5
    assert indicateurs.classement_commune(2023, "01002", ["Football", "Tennis"]).empty


def test_contours_departement_et_corse(environnement):
    assert len(carte.contours_communes_departement("01")["features"]) == 2
    assert len(carte.contours_communes_departement("2A")["features"]) == 1
    assert len(carte.contours_communes_departement("75")["features"]) == 0


def test_carte_avec_et_sans_donnees(environnement):
    figure = carte.creer_carte_communes(2023, "01", ["Football"])
    codes = {str(code) for trace in figure.data for code in trace.locations}
    assert {"01001", "01002"}.issubset(codes)
    assert any(trace.name == "Tennis" for trace in figure.data)
    vide = carte.creer_carte_communes(2023, "01", ["Football", "Tennis"])
    assert len(vide.data) == 1  # Les limites communales restent visibles en gris.
