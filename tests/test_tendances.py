"""Tests des indicateurs nationaux de la page Tendances."""

import pandas as pd
import pytest

from src.utils import tendances


@pytest.fixture(autouse=True)
def exemple(monkeypatch):
    """Quelques sports dont un absent en 2012 et un sport à effectif faible."""
    donnees = pd.DataFrame([
        (2012, "Football", 100_000), (2023, "Football", 120_000),
        (2012, "Tennis", 50_000), (2023, "Tennis", 30_000),
        (2012, "Petit sport", 50), (2023, "Petit sport", 150),
        (2023, "Sport récent", 22_000),
        (2019, "Football", 100_000), (2021, "Football", 80_000),
        (2019, "Tennis", 50_000), (2021, "Tennis", 40_000),
        (2019, "Sport récent", 20_000), (2021, "Sport récent", 20_000),
        (2019, "Petit sport", 80), (2021, "Petit sport", 80),
    ], columns=["annee", "sport", "licences"])
    monkeypatch.setattr(tendances, "resume_departements", lambda: donnees)
    tendances.licences_nationales.cache_clear()
    yield
    tendances.licences_nationales.cache_clear()


def test_agregation_reellement_par_sport():
    valeur = tendances.licences_nationales()
    assert valeur.loc[(valeur.annee == 2023) & (valeur.sport == "Football"), "licences"].item() == 120_000


def test_variations_ignore_petits_effectifs_et_sports_absents():
    resultat = tendances.variations()
    assert set(resultat.sport) == {"Football", "Tennis"}
    assert resultat.loc[resultat.sport == "Football", "variation"].item() == pytest.approx(20)
    assert resultat.loc[resultat.sport == "Tennis", "variation"].item() == pytest.approx(-40)


def test_inversion_periode_refusee():
    with pytest.raises(ValueError):
        tendances.variations(2023, 2012)


def test_covid_deux_periodes_et_effectifs_suffisants():
    resultat = tendances.effet_covid()
    assert "Petit sport" not in resultat.sport.tolist()
    foot = resultat.loc[resultat.sport == "Football"].iloc[0]
    assert foot.variation_2019_2021 == pytest.approx(-20)
    assert foot.variation_2021_2023 == pytest.approx(50)


def test_evolution_najoute_pas_zeros():
    resultat = tendances.evolution_sports(["Football", "Sport récent"])
    assert not ((resultat.sport == "Sport récent") & (resultat.annee == 2012)).any()


def test_evolution_requiert_deux_a_cinq_sports():
    with pytest.raises(ValueError):
        tendances.evolution_sports(["Football"])


def test_options_sports_et_defaut():
    assert "Petit sport" in tendances.sports_comparables()
    assert len(tendances.sports_par_defaut()) >= 2
