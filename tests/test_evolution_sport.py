"""Tests ciblés du commit 5, indépendants du dashboard et des données réelles."""

import sqlite3

import pandas as pd
import pytest

import config
from src.components.evolution import creer_evolution
from src.utils import couleurs, indicateurs


@pytest.fixture
def historique(tmp_path, monkeypatch):
    """Une série simple : tennis absent en 2022, deux fédérations pour le tennis."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "historique.db")
    with sqlite3.connect(config.DB_PATH) as cn:
        pd.DataFrame([
            (2021, "01", "100", 10),
            (2021, "01", "101", 20),
            (2021, "01", "102", 5),
            (2022, "01", "100", 15),
            (2023, "01", "100", 8),
            (2023, "01", "101", 30),
            (2023, "01", "102", 7),
        ], columns=["annee", "code_departement", "code_federation", "total"]).to_sql(
            "cleaned_licences_departements", cn, index=False
        )
        pd.DataFrame([
            ("100", "FF de Football", "unisport olympique"),
            ("101", "FF de Tennis", "unisport olympique"),
            ("102", "Fédération Française de Tennis", "unisport olympique"),
        ], columns=["code", "nom", "famille"]).to_sql(
            "cleaned_federations", cn, index=False
        )
        pd.DataFrame([
            ("01", "84"),
        ], columns=["code_departement", "code_region"]).to_sql(
            "cleaned_communes", cn, index=False
        )
    indicateurs.resume_departements.cache_clear()
    yield
    indicateurs.resume_departements.cache_clear()


def test_sport_unique_sur_plusieurs_annees(historique):
    valeurs = indicateurs.licences_par_annee("region", "84", sport="Tennis")
    assert dict(zip(valeurs["annee"], valeurs["licences"])) == {2021: 25, 2023: 37}


def test_ancien_mode_sans_sport(historique):
    valeurs = indicateurs.licences_par_annee("france")
    assert dict(zip(valeurs["annee"], valeurs["licences"])) == {
        2021: 35, 2022: 15, 2023: 45,
    }


def test_sport_choisi_prioritaire_sur_exclusions(historique):
    valeurs = indicateurs.licences_par_annee(
        "departement", "01", ["Tennis", "Football"], sport="Tennis"
    )
    assert valeurs["licences"].tolist() == [25, 37]
    sans_sport = indicateurs.licences_par_annee("departement", "01", ["Football"])
    assert sans_sport["licences"].tolist() == [25, 37]


def test_figure_sport_et_annees_manquantes(historique):
    fig = creer_evolution("france", None, [], 2023, sport="Tennis")
    assert list(fig.data[0].x) == [2021, 2023]
    assert list(fig.data[0].y) == [25, 37]
    assert list(fig.data[0].marker.color) == [couleurs.UNE_COULEUR, couleurs.MISE_EN_AVANT]


def test_sport_inconnu_figure_vide(historique):
    fig = creer_evolution("france", None, [], 2023, sport="Sport inconnu")
    assert not fig.data
    assert fig.layout.annotations
