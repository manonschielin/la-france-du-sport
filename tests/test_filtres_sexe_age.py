"""Tests du commit 7 : colonnes sélectionnées et cohérence aux trois échelles."""

import sqlite3

import pandas as pd
import pytest

import config
from src.components.pyramide import creer_pyramide
from src.utils import indicateurs
from src.utils.clean_data import COLONNES_AGE, creer_resume_departements


@pytest.fixture
def donnees(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "filtrage.sqlite")
    lignes = []
    for annee, code, departement, federation, total, valeurs in [
        (2022, "01001", "01", "100", 100, {"f_0_4": 4, "h_0_4": 6, "f_5_9": 2}),
        (2023, "01001", "01", "100", 200, {"f_0_4": 10, "h_0_4": 5, "f_5_9": 3}),
        (2023, "01002", "01", "100", 30, {"f_0_4": 2, "h_0_4": 8}),
        (2023, "02001", "02", "101", 50, {"f_0_4": 20, "h_0_4": 5}),
        (2023, "01001", "01", "600", 999, {"f_0_4": 900}),
    ]:
        ligne = dict.fromkeys(COLONNES_AGE, 0)
        ligne.update(valeurs)
        ligne.update(annee=annee, code_commune=code, code_departement=departement,
                     code_federation=federation, total=total)
        lignes.append(ligne)
    with sqlite3.connect(config.DB_PATH) as connexion:
        pd.DataFrame(lignes).to_sql("cleaned_licences", connexion, index=False)
        pd.DataFrame([
            ("01001", "01", "84", 1000),
            ("01002", "01", "84", 1000),
            ("02001", "02", "32", 1000),
        ], columns=["code_commune", "code_departement", "code_region", "population"]).to_sql(
            "cleaned_communes", connexion, index=False)
        pd.DataFrame([
            ("100", "FF de Football", "unisport olympique"),
            ("101", "FF de Tennis", "unisport olympique"),
            ("600", "Scolaire", "scolaire et universitaire"),
        ], columns=["code", "nom", "famille"]).to_sql("cleaned_federations", connexion, index=False)
        connexion.execute("CREATE INDEX idx_commune ON cleaned_licences(code_commune)")
        creer_resume_departements(connexion)
    caches = [indicateurs.liste_sports, indicateurs.donnees_regions,
              indicateurs.donnees_departements, indicateurs.donnees_communes,
              indicateurs.resume_departements, indicateurs.ages_departements,
              indicateurs.ages_commune, indicateurs.populations,
              indicateurs.licences_sport_communes]
    for cache in caches:
        cache.cache_clear()
    yield
    for cache in caches:
        cache.cache_clear()


def test_colonnes_selectionnees_et_validation():
    assert indicateurs.colonnes_selectionnees("f", ["0_4", "5_9"]) == ["f_0_4", "f_5_9"]
    assert len(indicateurs.colonnes_selectionnees()) == 18
    with pytest.raises(ValueError):
        indicateurs.colonnes_selectionnees("inconnu")
    with pytest.raises(ValueError):
        indicateurs.colonnes_selectionnees("f", ["inconnu"])


def test_resume_conserve_les_18_colonnes(donnees):
    with sqlite3.connect(config.DB_PATH) as connexion:
        noms = {r[1] for r in connexion.execute('PRAGMA table_info("cleaned_licences_departements")')}
    assert set(COLONNES_AGE).issubset(noms)


def test_mode_tous_conserve_total_et_filtres_additionnent(donnees):
    base = indicateurs.donnees_regions(2023).set_index(["code_region", "sport"])
    assert base.loc[("84", "Football"), "licences"] == 230
    filtres = indicateurs.sports_par_region(2023, sexe="f", tranches=["0_4"])
    assert filtres.set_index(["code_region", "sport"]).loc[("84", "Football"), "licences"] == 12
    tranche = indicateurs.sports_par_region(2023, tranches=["0_4"])
    assert tranche.set_index(["code_region", "sport"]).loc[("84", "Football"), "licences"] == 25
    assert "Scolaire" not in filtres["sport"].tolist()


def test_departements_communes_et_classements(donnees):
    dep = indicateurs.classement_departement(2023, "01", sexe="h", tranches=["0_4"])
    assert dep.iloc[0]["licences"] == 13
    commune = indicateurs.classement_commune(2023, "01001", sexe="f", tranches=["0_4"])
    assert commune.iloc[0]["licences"] == 10
    top = indicateurs.sport_numero_un_communes(2023, ["01001", "01002"], sexe="f", tranches=["0_4"])
    assert set(top["licences"]) == {10, 2}


def test_evolution_et_taux_suivent_filtres(donnees):
    ancien = indicateurs.licences_par_annee("region", "84")
    assert ancien.set_index("annee").loc[2023, "licences"] == 230
    recent = indicateurs.licences_par_annee("region", "84", sexe="f", tranches=["0_4"])
    assert recent.set_index("annee").loc[2022, "licences"] == 4
    assert recent.set_index("annee").loc[2023, "licences"] == 12
    commune = indicateurs.licences_par_annee("commune", "01001", sexe="h", tranches=["0_4"])
    assert commune.set_index("annee").loc[2023, "licences"] == 5
    taux = indicateurs.licences_pour_1000(2023, "Football", "departement", "f", ["0_4"])
    assert taux.set_index("code").loc["01", "taux"] == 6
    taux_com = indicateurs.licences_pour_1000(2023, "Football", "commune", "f", ["0_4"])
    assert taux_com.set_index("code").loc["01001", "taux"] == 10


def test_pyramide_masque_sexe_et_surligne_ages(donnees):
    fig = creer_pyramide(2023, "region", "84", None, [], "f", ["0_4"])
    assert len(fig.data) == 1
    assert fig.data[0].name == "Femmes"
    assert list(fig.data[0].marker.color)[0] != list(fig.data[0].marker.color)[1]
    assert list(fig.data[0].x)[0] == 12
