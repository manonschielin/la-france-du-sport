"""Tests des profils nationaux sur des données synthétiques."""

import pandas as pd
import pytest

from src.utils import profils
from src.utils.indicateurs import COLONNES_AGE


@pytest.fixture(autouse=True)
def donnees_exemple(monkeypatch):
    """Un sport féminin, un masculin, un petit et un sport récent."""
    lignes = []
    for annee, sport, f, h in [
        (2012, "Tennis", 4000, 6000),
        (2023, "Tennis", 8000, 12000),
        (2023, "Danse", 16000, 4000),
        (2023, "Rugby", 2000, 18000),
        (2023, "Petit", 80, 20),
        (2023, "Sport récent", 12000, 3000),
    ]:
        valeurs = {col: 0 for col in COLONNES_AGE}
        valeurs["f_10_14"] = f // 2
        valeurs["f_20_29"] = f - f // 2
        valeurs["h_10_14"] = h // 4
        valeurs["h_20_29"] = h - h // 4
        lignes.append({"annee": annee, "sport": sport, **valeurs})
    monkeypatch.setattr(profils, "resume_departements", lambda: pd.DataFrame(lignes))
    profils.donnees_profils.cache_clear()
    yield
    profils.donnees_profils.cache_clear()


def test_agregation_sexe():
    tennis = profils.donnees_profils().query("annee == 2023 and sport == 'Tennis'").iloc[0]
    assert (tennis.femmes, tennis.hommes, tennis.renseignes) == (8000, 12000, 20000)


def test_part_femmes_et_seuil():
    resultat = profils.parts_femmes(2023)
    assert "Petit" not in resultat.sport.tolist()
    assert resultat.iloc[0].sport == "Danse"
    assert resultat.loc[resultat.sport == "Danse", "part_femmes"].item() == pytest.approx(80)
    assert resultat.loc[resultat.sport == "Rugby", "part_femmes"].item() == pytest.approx(10)


def test_chaleur_normalisee_par_sport():
    resultat = profils.repartition_ages(2023, nombre=5)
    assert resultat.groupby("sport")["pourcentage"].sum().eq(100).all()
    tennis = resultat.query("sport == 'Tennis' and tranche == '10-14 ans'")
    assert tennis.iloc[0].licences == 7000


def test_evolution_ne_cree_pas_donnees_absentes():
    resultat = profils.evolution_part_femmes(["Tennis", "Sport récent"])
    assert len(resultat.query("sport == 'Tennis'")) == 2
    assert resultat.query("sport == 'Sport récent'").annee.tolist() == [2023]


def test_evolution_controle_nombre_sports():
    with pytest.raises(ValueError):
        profils.evolution_part_femmes([])
    with pytest.raises(ValueError):
        profils.evolution_part_femmes(["a", "b", "c", "d", "e", "f"])


def test_resume_sans_age_demande_reconstruction(monkeypatch):
    profils.donnees_profils.cache_clear()
    monkeypatch.setattr(profils, "resume_departements", lambda: pd.DataFrame([
        {"annee": 2023, "sport": "Tennis", "licences": 20000}
    ]))
    with pytest.raises(ValueError, match="rebuild_resume"):
        profils.donnees_profils()


def test_licences_par_tranche_age():
    resultat = profils.licences_par_tranche_age(2023).set_index("tranche")
    assert len(resultat) == 9
    assert resultat.loc["10-14 ans", "licences"] == 28295
    assert resultat.loc["20-29 ans", "licences"] == 46805
    assert resultat["licences"].sum() == 75100
    assert (resultat["femmes"] + resultat["hommes"] == resultat["licences"]).all()


def test_tranches_age_absence_donnees():
    resultat = profils.licences_par_tranche_age(2022)
    assert len(resultat) == 9
    assert resultat["licences"].sum() == 0


def test_graphique_tranches_age_utilise_annee():
    pytest.importorskip("dash")
    from src.pages.profils import graphique_tranches_age

    figure = graphique_tranches_age(2023)
    assert len(figure.data) == 1
    assert figure.data[0].orientation == "h"
    assert figure.data[0].y[-1] == "20-29 ans"
    assert len(graphique_tranches_age(2022).data) == 0
