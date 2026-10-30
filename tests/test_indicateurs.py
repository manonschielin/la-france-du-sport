"""Tests reproductibles des indicateurs sur une petite base SQLite fictive."""

import sqlite3

import pandas as pd
import pytest

import config
from src.utils import indicateurs


@pytest.fixture
def base_test(tmp_path, monkeypatch):
    """Prépare deux régions et plusieurs fédérations, sans données externes."""
    chemin = tmp_path / "sport_test.sqlite"
    monkeypatch.setattr(config, "DB_PATH", chemin)
    indicateurs.liste_sports.cache_clear()
    indicateurs.donnees_regions.cache_clear()
    indicateurs.donnees_departements.cache_clear()
    with sqlite3.connect(chemin) as connexion:
        pd.DataFrame(
            [
                ("01", "84"), ("01", "84"),  # Deux communes dans le même département.
                ("02", "32"), ("2A", "94"),
            ], columns=["code_departement", "code_region"]
        ).to_sql("cleaned_communes", connexion, index=False)
        pd.DataFrame(
            [
                (2023, "01", "100", 100),  # Football.
                (2023, "01", "101", 40),  # Tennis.
                (2023, "01", "102", 20),  # Autre fédération de tennis.
                (2023, "02", "100", 10),
                (2023, "02", "101", 70),
                (2023, "2A", "101", 8),
                (2023, "01", "600", 999),  # Fédé scolaire à exclure.
                (2022, "01", "100", 4),
            ], columns=["annee", "code_departement", "code_federation", "total"]
        ).to_sql("cleaned_licences", connexion, index=False)
        pd.DataFrame(
            [
                ("100", "FF de Football", "unisport olympique"),
                ("101", "FF de Tennis", "unisport olympique"),
                ("102", "Fédération Française de Tennis", "unisport olympique"),
                ("600", "Sport scolaire", "scolaire et universitaire"),
            ], columns=["code", "nom", "famille"]
        ).to_sql("cleaned_federations", connexion, index=False)
    yield chemin
    indicateurs.liste_sports.cache_clear()
    indicateurs.donnees_regions.cache_clear()
    indicateurs.donnees_departements.cache_clear()


def test_pas_de_multiplication_des_licences(base_test):
    resultat = indicateurs.donnees_regions(2023)
    auvergne = resultat[resultat["code_region"] == "84"]
    assert auvergne["licences"].sum() == 160
    assert auvergne.set_index("sport").loc["Tennis", "licences"] == 60


def test_exclusions_et_classement(base_test):
    initial = indicateurs.sport_numero_un(2023).set_index("code_region")
    assert initial.loc["84", "sport"] == "Football"
    apres = indicateurs.sport_numero_un(2023, ["Football"]).set_index("code_region")
    assert apres.loc["84", "sport"] == "Tennis"
    assert indicateurs.classement_region(2023, "84", ["Football"])["sport"].tolist() == ["Tennis"]
    assert indicateurs.classement_region(2023, "84", ["Football", "Tennis"]).empty
    assert indicateurs.donnees_regions(2023)["licences"].sum() == 248


def test_departements_et_codes_corse(base_test):
    resultat = indicateurs.sport_numero_un_departements(2023, ["01", "2A"], ["Football"])
    assert set(resultat["code_departement"]) == {"01", "2A"}
    assert resultat.set_index("code_departement").loc["01", "licences"] == 60


def test_menu_sans_doublons(base_test):
    noms = indicateurs.liste_sports_uniques()["sport"].tolist()
    assert noms.count("Tennis") == 1
    assert "Sport scolaire" not in noms


def test_refuse_un_departement_multiregion(base_test):
    with sqlite3.connect(base_test) as connexion:
        connexion.execute("INSERT INTO cleaned_communes VALUES ('01', '32')")
    indicateurs.donnees_regions.cache_clear()
    with pytest.raises(ValueError, match="ambiguë"):
        indicateurs.donnees_regions(2023)
