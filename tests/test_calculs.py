"""Commit 8 : tests des calculs métier sur une base SQLite isolée.

Aucune donnée réelle ni accès réseau : les valeurs attendues sont déterminées à la main.
"""

import sqlite3

import pandas as pd
import pytest

import config
from src.utils import indicateurs
from src.utils.clean_data import COLONNES_AGE, creer_resume_departements


@pytest.fixture
def base_calculs(tmp_path, monkeypatch):
    """Deux régions, trois départements, Paris et une commune trop petite."""
    chemin = tmp_path / "calculs_commit8.sqlite"
    monkeypatch.setattr(config, "DB_PATH", chemin)

    def ligne(annee, commune, departement, federation, total, **ages):
        valeurs = dict.fromkeys(COLONNES_AGE, 0)
        valeurs.update(ages)
        return dict(annee=annee, code_commune=commune,
                    code_departement=departement, code_federation=federation,
                    total=total, **valeurs)

    lignes = [
        ligne(2022, "01001", "01", "100", 25, f_0_4=3, h_0_4=4, f_5_9=2),
        ligne(2023, "01001", "01", "100", 100, f_0_4=10, h_0_4=20, f_5_9=5, h_5_9=7),
        ligne(2023, "01002", "01", "100", 30, f_0_4=2, h_0_4=8),
        ligne(2023, "01001", "01", "101", 40, f_0_4=6, h_0_4=4),
        ligne(2023, "02001", "02", "101", 50, f_0_4=12, h_0_4=3),
        ligne(2023, "75101", "75", "100", 11, f_0_4=3, h_0_4=2),
        ligne(2023, "75120", "75", "100", 9, f_0_4=4, h_0_4=1),
        ligne(2023, "75056", "75", "100", 5, f_0_4=1, h_0_4=1),
        # Une fédération scolaire ne doit pas apparaître dans ces indicateurs.
        ligne(2023, "01001", "01", "600", 900, f_0_4=500),
    ]
    communes = [
        ("01001", "01", "84", 1000),
        ("01002", "01", "84", 100),
        ("02001", "02", "32", 2000),
        ("75056", "75", "11", 10000),
        ("75101", "75", "11", 1000),
        ("75120", "75", "11", 1000),
    ]
    federations = [
        ("100", "FF de Football", "unisport olympique"),
        ("101", "FF de Tennis", "unisport olympique"),
        ("600", "Fédération scolaire", "scolaire et universitaire"),
    ]
    with sqlite3.connect(chemin) as connexion:
        pd.DataFrame(lignes).to_sql("cleaned_licences", connexion, index=False)
        pd.DataFrame(communes, columns=["code_commune", "code_departement",
                "code_region", "population"]).to_sql("cleaned_communes", connexion, index=False)
        pd.DataFrame(federations, columns=["code", "nom", "famille"]).to_sql(
            "cleaned_federations", connexion, index=False)
        connexion.execute("CREATE INDEX idx_commune ON cleaned_licences (code_commune)")
        creer_resume_departements(connexion)

    caches = [indicateurs.liste_sports, indicateurs.resume_departements,
              indicateurs.licences_commune, indicateurs.populations,
              indicateurs.licences_sport_communes, indicateurs.ages_departements,
              indicateurs.ages_commune, indicateurs.donnees_regions,
              indicateurs.donnees_departements, indicateurs.donnees_communes]
    for fonction in caches:
        fonction.cache_clear()
    yield chemin
    for fonction in caches:
        fonction.cache_clear()


def valeurs_annuelles(**kwargs):
    """Facilite la comparaison sans dépendre de l'ordre du DataFrame."""
    resultat = indicateurs.licences_par_annee(**kwargs)
    return dict(zip(resultat["annee"], resultat["licences"]))


@pytest.mark.parametrize(("niveau", "code", "attendu"), [
    ("france", None, {2022: 25, 2023: 245}),
    ("region", "84", {2022: 25, 2023: 170}),
    ("departement", "01", {2022: 25, 2023: 170}),
    ("commune", "01001", {2022: 25, 2023: 140}),
])
def test_licences_par_annee_toutes_echelles(base_calculs, niveau, code, attendu):
    """Comparaison des sommes non filtrées à quatre niveaux géographiques."""
    assert valeurs_annuelles(niveau=niveau, code=code) == attendu


def test_licences_par_annee_paris_regroupe_arrondissements(base_calculs):
    """Paris inclut la ville et les arrondissements même sans filtre sexe/âge."""
    assert valeurs_annuelles(niveau="commune", code="75056") == {2023: 25}
    assert valeurs_annuelles(niveau="commune", code="75056", sexe="f", tranches=["0_4"]) == {2023: 8}


@pytest.mark.parametrize(("niveau", "code", "attendu"), [
    ("france", None, 38),
    ("region", "84", 18),
    ("departement", "01", 18),
    ("commune", "01001", 16),
])
def test_evolution_filtre_femmes_zero_quatre(base_calculs, niveau, code, attendu):
    """Le même filtre utilise les colonnes f_0_4 à toutes les échelles."""
    assert valeurs_annuelles(niveau=niveau, code=code, sexe="f", tranches=["0_4"])[2023] == attendu


def test_filtre_femmes_et_hommes_est_la_somme(base_calculs):
    """Sexe Tous + âge ciblé = somme des données femmes et hommes."""
    selection = ["0_4", "5_9"]
    for niveau, code in [("france", None), ("region", "84"),
                         ("departement", "01"), ("commune", "01001")]:
        femmes = valeurs_annuelles(niveau=niveau, code=code, sexe="f", tranches=selection)
        hommes = valeurs_annuelles(niveau=niveau, code=code, sexe="h", tranches=selection)
        deux = valeurs_annuelles(niveau=niveau, code=code, sexe="tous", tranches=selection)
        assert deux[2023] == femmes[2023] + hommes[2023]
    # Le total brut inclut ici les licences sans sexe/âge renseigné.
    region_filtre = valeurs_annuelles(niveau="region", code="84",
                                     sexe="tous", tranches=selection)
    assert valeurs_annuelles(niveau="region", code="84")[2023] > region_filtre[2023]


def test_annees_exclusions_et_priorite_sport(base_calculs):
    """Les exclusions ne priment pas sur le sport explicitement analysé."""
    assert valeurs_annuelles(niveau="region", code="84", exclusions=["Football"]) == {2023: 40}
    assert valeurs_annuelles(niveau="region", code="84", exclusions=["Football"],
                             sport="Football") == {2022: 25, 2023: 130}


@pytest.mark.parametrize(("code", "attendu"), [
    ("75101", "75056"), ("75120", "75056"),
    ("69381", "69123"), ("69389", "69123"),
    ("13201", "13055"), ("13216", "13055"),
    ("01001", "01001"), ("75121", "75121"),
])
def test_code_ville(code, attendu):
    assert indicateurs.code_ville(code) == attendu


def test_codes_licences_commune_paris_20_arrondissements():
    codes = indicateurs.codes_licences_commune("75056")
    assert len(codes) == 21
    assert len(set(codes)) == 21
    assert set(codes) == {"75056", *(f"751{i:02d}" for i in range(1, 21))}
    assert indicateurs.codes_licences_commune("01001") == ["01001"]
    assert len(indicateurs.codes_licences_commune("69123")) == 10
    assert len(indicateurs.codes_licences_commune("13055")) == 17


def test_licences_pour_1000_trois_echelles_et_seuil(base_calculs):
    region = indicateurs.licences_pour_1000(2023, "Football", "region").set_index("code")
    assert region.loc["84", "licences"] == 130
    assert region.loc["84", "taux"] == 118.2  # 130 / 1100 * 1000
    dep = indicateurs.licences_pour_1000(2023, "Football", "departement", "f", ["0_4"])
    assert dep.set_index("code").loc["01", "taux"] == 10.9  # 12 / 1100 * 1000
    commune = indicateurs.licences_pour_1000(2023, "Football", "commune").set_index("code")
    assert pd.isna(commune.loc["01002", "taux"])  # population < 200
    assert commune.loc["75056", "licences"] == 25
    assert commune.loc["75056", "population"] == 10000  # Ne pas compter deux fois Paris.
    assert commune.loc["75056", "taux"] == 2.5
    assert pd.isna(commune.loc["02001", "taux"])  # aucune licence football


def test_pyramide_ages_selon_territoire_et_filtres(base_calculs):
    pyramide = indicateurs.pyramide_ages(2023, "region", "84")
    par_tranche = pyramide.set_index("tranche")
    assert par_tranche.loc["0-4 ans", "femmes"] == 18  # 10+2+6
    assert par_tranche.loc["0-4 ans", "hommes"] == 32  # 20+8+4
    assert par_tranche.loc["5-9 ans", "femmes"] == 5
    assert par_tranche.loc["5-9 ans", "hommes"] == 7
    football = indicateurs.pyramide_ages(2023, "commune", "75056", sport="Football")
    assert football.set_index("tranche").loc["0-4 ans", "femmes"] == 8
    sans_football = indicateurs.pyramide_ages(2023, "departement", "01", exclusions=["Football"])
    assert sans_football.set_index("tranche").loc["0-4 ans", "femmes"] == 6
    assert sans_football.set_index("tranche").loc["0-4 ans", "hommes"] == 4
    # La fonction renvoie les deux séries brutes ; la visibilité est gérée par le composant Plotly.
    assert indicateurs.pyramide_ages(2023, "region", "84", sexe="f").equals(pyramide)
