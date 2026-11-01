"""Tests du commit 4 : cartes par sport, arrondissements et taux absents."""
import json
import sqlite3

import pandas as pd
import pytest

import config
from src.components import carte
from src.utils import indicateurs


@pytest.fixture
def donnees_taux(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "DATA_RAW_DIR", tmp_path)
    with sqlite3.connect(config.DB_PATH) as cn:
        pd.DataFrame([
            (2023, "75101", "75", "100", 20),
            (2023, "01001", "01", "100", 4),
            (2023, "01002", "01", "101", 10),
        ], columns=["annee", "code_commune", "code_departement", "code_federation", "total"]).to_sql(
            "cleaned_licences", cn, index=False)
        pd.DataFrame([
            ("100", "FF de Football", "unisport olympique"),
            ("101", "FF de Tennis", "unisport olympique"),
        ], columns=["code", "nom", "famille"]).to_sql("cleaned_federations", cn, index=False)
        pd.DataFrame([
            ("75056", "75", "11", 10000),
            ("75101", "75", "11", 1000),
            ("01001", "01", "84", 100),
            ("01002", "01", "84", 1000),
        ], columns=["code_commune", "code_departement", "code_region", "population"]).to_sql(
            "cleaned_communes", cn, index=False)
        pd.DataFrame([
            (2023, "75", "100", 20),
            (2023, "01", "100", 4),
            (2023, "01", "101", 10),
        ], columns=["annee", "code_departement", "code_federation", "total"]).to_sql(
            "cleaned_licences_departements", cn, index=False)
    regions = [("11", "Île-de-France"), ("84", "Auvergne")]
    deps = [("75", "Paris", "11"), ("01", "Ain", "84")]
    communes = [("75056", "Paris"), ("01001", "Petite"), ("01002", "Grande")]
    def feature(code, nom, extra=None):
        return {"type": "Feature", "properties": {"code": code, "nom": nom, **(extra or {})},
                "geometry": {"type": "Polygon", "coordinates": [[[2, 46], [3, 46], [3, 47], [2, 47], [2, 46]]]}}
    for nom, zones in [
        ("regions", [feature(a, b) for a, b in regions]),
        ("departements", [feature(a, b, {"region": r}) for a, b, r in deps]),
        ("communes", [feature(a, b) for a, b in communes]),
    ]:
        (tmp_path / f"contours_{nom}.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": zones}), encoding="utf-8")
    for cached in (indicateurs.populations, indicateurs.liste_sports,
                   indicateurs.licences_sport_communes, indicateurs.resume_departements,
                   carte.contours_regions, carte.contours_departements,
                   carte._index_contours_communes):
        cached.cache_clear()
    yield
    for cached in (indicateurs.populations, indicateurs.liste_sports,
                   indicateurs.licences_sport_communes, indicateurs.resume_departements,
                   carte.contours_regions, carte.contours_departements,
                   carte._index_contours_communes):
        cached.cache_clear()


def test_taux_communes_et_paris(donnees_taux):
    taux = indicateurs.licences_pour_1000(2023, "Football", "commune").set_index("code")
    assert taux.loc["75056", "licences"] == 20
    assert taux.loc["75056", "population"] == 10000  # Ne pas doubler Paris
    assert taux.loc["75056", "taux"] == 2
    assert pd.isna(taux.loc["01001", "taux"])  # moins de 200 habitants
    assert pd.isna(taux.loc["01002", "taux"])  # aucune licence football


def test_cartes_trois_niveaux_et_gris(donnees_taux):
    for niveau, region, dep in [
        ("region", None, None), ("departement", "84", None),
        ("commune", None, "01")
    ]:
        fig = carte.creer_carte_taux(2023, "Football", niveau,
                                    code_region=region, code_departement=dep)
        assert len(fig.data) == (1 if niveau == "commune" else 2)
        assert fig.data[0].showscale is False
        assert "1 000" in fig.layout.title.text
    # Le gris couvre les deux communes, même celle sans taux exploitable.
    fig = carte.creer_carte_taux(2023, "Football", "commune", code_departement="01")
    assert set(fig.data[0].locations) == {"01001", "01002"}
    assert len(fig.data) == 1  # Les deux sont grises (taux manquant / population trop petite)


def test_aucune_licence_pour_sport_inconnu(donnees_taux):
    fig = carte.creer_carte_taux(2023, "Inexistant", "commune", code_departement="01")
    assert len(fig.data) == 1
