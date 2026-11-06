"""Tests de l'histogramme des communes (vraies classes, pas px.bar)."""

import sqlite3

import pandas as pd
import pytest

import config
from src.utils import distribution, indicateurs


@pytest.fixture
def petite_base(tmp_path, monkeypatch):
    """Base illustrative : Paris + arrondissements, petite commune, commune sans licences."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    with sqlite3.connect(config.DB_PATH) as connexion:
        pd.DataFrame([
            (2023, "75101", "100", 20),
            (2023, "75102", "100", 30),
            (2023, "75056", "101", 50),
            (2023, "01001", "100", 10),
            (2023, "01002", "100", 15),
            (2023, "01002", "101", 5),
            (2022, "01002", "100", 40),
        ], columns=["annee", "code_commune", "code_federation", "total"]).to_sql(
            "cleaned_licences", connexion, index=False)
        pd.DataFrame([
            ("100", "FF de Football", "unisport olympique"),
            ("101", "FF de Tennis", "unisport olympique"),
        ], columns=["code", "nom", "famille"]).to_sql(
            "cleaned_federations", connexion, index=False)
        pd.DataFrame([
            ("75056", 1000), ("75101", 400), ("75102", 600),
            ("01001", 100), ("01002", 1000), ("01003", 500),
        ], columns=["code_commune", "population"]).to_sql(
            "cleaned_communes", connexion, index=False)
    indicateurs.populations.cache_clear()
    indicateurs.liste_sports.cache_clear()
    distribution._licences_communes_annee.cache_clear()
    yield
    indicateurs.populations.cache_clear()
    indicateurs.liste_sports.cache_clear()
    distribution._licences_communes_annee.cache_clear()


def test_tous_sports_et_arrondissements_sans_doubler_population(petite_base):
    result = distribution.distribution_communes(2023).set_index("code")
    assert set(result.index) == {"75056", "01002"}
    assert result.loc["75056", "licences"] == 100
    assert result.loc["75056", "population"] == 1000
    assert result.loc["75056", "taux"] == pytest.approx(100)
    assert result.loc["01002", "taux"] == pytest.approx(20)


def test_selection_sport_et_petites_communes(petite_base):
    result = distribution.distribution_communes(2023, "Football", 200).set_index("code")
    assert set(result.index) == {"75056", "01002"}
    assert result.loc["75056", "taux"] == pytest.approx(50)
    assert result.loc["01002", "taux"] == pytest.approx(15)
    sans_seuil = distribution.distribution_communes(2023, "Football", 0)
    assert "01001" in set(sans_seuil["code"])


def test_annee_manquante_et_sport_inconnu(petite_base):
    assert distribution.distribution_communes(2021).empty
    assert distribution.distribution_communes(2023, "Sport inconnu").empty


def test_seuil_invalide(petite_base):
    with pytest.raises(ValueError):
        distribution.distribution_communes(2023, population_minimum=-1)


def test_histogramme_plotly_express(petite_base):
    pytest.importorskip("dash")
    from src.pages.fetiches import creer_histogramme

    fig, message = creer_histogramme(2023, "Football", True, "complet")
    assert len(fig.data) == 1
    assert fig.data[0].type == "histogram"
    assert len(fig.data[0].x) == 2
    assert "2 communes" in message
    assert fig.layout.yaxis.title.text == "Nombre de communes"
    fig_vide, message_vide = creer_histogramme(2021, None, True)
    assert len(fig_vide.data) == 0
    assert "Aucune" in message_vide


def test_mode_principal_masque_uniquement_les_valeurs_extremes():
    valeurs = pd.DataFrame({"taux": [float(x) for x in range(1, 101)] + [2450.6]})
    origin = valeurs.copy(deep=True)
    vue, seuil, exclus = distribution.limiter_distribution(valeurs, "principal")
    assert exclus == 1
    assert 100 <= seuil < 2450.6
    assert len(vue) == 100
    assert vue["taux"].max() == 100
    pd.testing.assert_frame_equal(valeurs, origin)


def test_mode_complet_conserve_toutes_les_communes():
    valeurs = pd.DataFrame({"taux": [float(x) for x in range(1, 101)] + [2450.6]})
    vue, seuil, exclus = distribution.limiter_distribution(valeurs, "complet")
    assert exclus == 1
    assert seuil is not None
    assert len(vue) == len(valeurs)
    assert vue["taux"].max() == 2450.6


def test_modes_sur_donnees_vides_et_mode_inconnu():
    vide = pd.DataFrame(columns=["taux"])
    vue, seuil, exclus = distribution.limiter_distribution(vide)
    assert vue.empty and seuil is None and exclus == 0
    with pytest.raises(ValueError):
        distribution.limiter_distribution(vide, "invalide")
