"""Distribution nationale des communes selon leurs licences pour 1 000 habitants.

Une ligne de la distribution correspond à une commune, pas à une fédération.
Les licences sans commune exploitable et les populations absentes ne sont pas imputées.
"""

import sqlite3
from functools import lru_cache

import pandas as pd

import config
from src.utils.indicateurs import (
    FAMILLES_UNISPORT,
    code_ville,
    codes_federations,
    populations,
)


@lru_cache(maxsize=20)
def _licences_communes_annee(annee: int) -> pd.DataFrame:
    """Agrège toutes les fédérations unisports, avant regroupement des arrondissements."""
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            """SELECT l.code_commune AS code, SUM(l.total) AS licences
               FROM cleaned_licences AS l
               JOIN cleaned_federations AS f ON l.code_federation = f.code
               WHERE l.annee = ? AND f.famille IN (?, ?)
               GROUP BY l.code_commune""",
            connexion,
            params=(annee, *FAMILLES_UNISPORT),
        )
    return _regrouper_arrondissements(donnees)


def _regrouper_arrondissements(donnees: pd.DataFrame) -> pd.DataFrame:
    """Ramène les codes d'arrondissement à leur ville sans perdre les licences."""
    donnees = donnees.copy()
    if donnees.empty:
        return pd.DataFrame(columns=["code", "licences"])
    donnees["code"] = donnees["code"].astype(str).map(code_ville)
    donnees["licences"] = pd.to_numeric(donnees["licences"], errors="coerce")
    return donnees.groupby("code", as_index=False)[["licences"]].sum(min_count=1)


def distribution_communes(
    annee: int,
    sport: str | None = None,
    population_minimum: int = 200,
) -> pd.DataFrame:
    """Retourne une ligne par commune dotée d'un effectif et d'une population valides.

    La mesure est un nombre de licences pour 1 000 habitants, PAS une proportion
    de personnes uniques. Une commune sans ligne de licence n'est pas assimilée à zéro.
    """
    if population_minimum < 0:
        raise ValueError("La population minimale doit être positive ou nulle.")

    if sport:
        codes = codes_federations(sport)
        if not codes:
            return pd.DataFrame(columns=["code", "population", "licences", "taux"])
        marqueurs = ", ".join("?" for _ in codes)
        with sqlite3.connect(config.DB_PATH) as connexion:
            licences = pd.read_sql_query(
                f"""SELECT code_commune AS code, SUM(total) AS licences
                    FROM cleaned_licences
                    WHERE annee = ? AND code_federation IN ({marqueurs})
                    GROUP BY code_commune""",
                connexion,
                params=(annee, *codes),
            )
        licences = _regrouper_arrondissements(licences)
    else:
        licences = _licences_communes_annee(annee).copy()

    population = populations("commune")[['code', 'population']].copy()
    population["code"] = population["code"].astype(str)
    resultat = population.merge(licences, on="code", how="inner", validate="one_to_one")
    resultat["population"] = pd.to_numeric(resultat["population"], errors="coerce")
    resultat["licences"] = pd.to_numeric(resultat["licences"], errors="coerce")
    resultat = resultat.loc[
        (resultat["population"] > 0)
        & (resultat["population"] >= population_minimum)
        & resultat["licences"].notna()
        & (resultat["licences"] >= 0)
    ].copy()
    resultat["taux"] = resultat["licences"] / resultat["population"] * 1000
    # DEBUG : afficher les 10 communes avec les taux les plus élevés
    print(f"\n--- TOP 10 DES TAUX LES PLUS ÉLEVÉS ({annee}) ---")
    print(f"Sport : {sport if sport else 'Tous les sports'}")
    print(f"Population minimale : {population_minimum} habitants\n")

    print(
        resultat.nlargest(10, "taux")[
            ["code", "population", "licences", "taux"]
        ].to_string(index=False)
    )
    return resultat.sort_values("code").reset_index(drop=True)


def limiter_distribution(
    donnees: pd.DataFrame,
    affichage: str = "principal",
) -> tuple[pd.DataFrame, float | None, int]:
    """Filtre seulement la vue : renvoie données affichées, P99 et nombre masqué.

    Le seuil est calculé sur toutes les observations ; la table d'origine est intacte.
    """
    if affichage not in {"principal", "complet"}:
        raise ValueError("Mode d'affichage inconnu.")
    if donnees.empty:
        return donnees.copy(), None, 0

    seuil = float(donnees["taux"].quantile(0.99))
    extremes = donnees["taux"] > seuil
    nb_extremes = int(extremes.sum())
    if affichage == "principal":
        return donnees.loc[~extremes].copy(), seuil, nb_extremes
    return donnees.copy(), seuil, nb_extremes
