
"""Calcul des indicateurs sportifs du dashboard."""

import sqlite3
from functools import lru_cache

import pandas as pd

import config
from src.utils.referentiel import nom_sport


@lru_cache(maxsize=1)
def liste_sports() -> pd.DataFrame:
    """Retourne les fédérations unisports disponibles."""
    with sqlite3.connect(config.DB_PATH) as connexion:
        sports = pd.read_sql_query(
            """
            SELECT code, nom
            FROM cleaned_federations
            WHERE famille IN (
                'unisport olympique',
                'unisport non olympique'
            )
            ORDER BY nom
            """,
            connexion,
        )

    sports["code"] = sports["code"].astype(str)
    sports["sport"] = sports["nom"].apply(nom_sport)

    return sports.sort_values("sport").reset_index(drop=True)


@lru_cache(maxsize=20)
def donnees_regions(annee: int) -> pd.DataFrame:
    """Charge les licences par région et fédération."""
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            """
            SELECT
                d.code_region,
                l.code_federation,
                f.nom AS federation,
                SUM(l.total) AS licences
            FROM cleaned_licences AS l
            JOIN (
                SELECT DISTINCT code_departement, code_region
                FROM cleaned_communes
            ) AS d
                ON l.code_departement = d.code_departement
            JOIN cleaned_federations AS f
                ON l.code_federation = f.code
            WHERE l.annee = ?
              AND f.famille IN (
                  'unisport olympique',
                  'unisport non olympique'
              )
            GROUP BY
                d.code_region,
                l.code_federation,
                f.nom
            """,
            connexion,
            params=(annee,),
        )

    donnees["code_region"] = (
        donnees["code_region"].astype(str).str.zfill(2)
    )
    donnees["code_federation"] = (
        donnees["code_federation"].astype(str)
    )

    donnees["sport"] = (
        donnees["federation"].apply(nom_sport)
    )

    donnees = (
        donnees.groupby(
            ["code_region", "sport"],
            as_index=False,
        )["licences"]
        .sum()
    )

    donnees["code_federation"] = donnees["sport"]

    return donnees


def sports_par_region(
    annee: int,
    exclusions: list[str] | None = None,
) -> pd.DataFrame:
    """Retourne les licences en excluant les sports choisis."""
    donnees = donnees_regions(annee)

    if not exclusions:
        return donnees.copy()

    return donnees.loc[
        ~donnees["sport"].isin(exclusions)
    ].copy()



def sport_numero_un(
    annee: int,
    exclusions: list[str] | None = None,
) -> pd.DataFrame:
    """Trouve la fédération dominante dans chaque région."""
    donnees = sports_par_region(annee, exclusions)

    if donnees.empty:
        return donnees

    indices = donnees.groupby("code_region")["licences"].idxmax()

    return donnees.loc[indices].reset_index(drop=True)


def classement_region(
    annee: int,
    code_region: str,
    exclusions: list[str] | None = None,
) -> pd.DataFrame:
    """Retourne les dix fédérations dominantes d'une région."""
    donnees = sports_par_region(annee, exclusions)

    region = donnees.loc[
        donnees["code_region"] == str(code_region).zfill(2)
    ]

    return (
        region.sort_values("licences", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )


def liste_sports_uniques() -> pd.DataFrame:
    """Retourne les noms de sports uniques pour les filtres."""
    sports = liste_sports()

    return (
        sports[["sport"]]
        .drop_duplicates()
        .sort_values("sport")
        .reset_index(drop=True)
    )



@lru_cache(maxsize=20)
def donnees_departements(annee: int) -> pd.DataFrame:
    """Charge les licences par département et par sport."""
    with sqlite3.connect(config.DB_PATH) as connexion:
                donnees = pd.read_sql_query(
            """
            SELECT
                s.code_departement,
                f.nom AS federation,
                s.licences
            FROM (
                SELECT
                    code_departement,
                    code_federation,
                    SUM(total) AS licences
                FROM cleaned_licences
                WHERE annee = ?
                GROUP BY code_departement, code_federation
            ) AS s
            JOIN cleaned_federations AS f
                ON s.code_federation = f.code
            WHERE f.famille IN (
                'unisport olympique',
                'unisport non olympique'
            )
            """,
            connexion,
            params=(annee,),
        )
        
    donnees["sport"] = donnees["federation"].apply(nom_sport)

    return donnees.groupby(
        ["code_departement", "sport"],
        as_index=False,
    )["licences"].sum()


def sport_numero_un_departements(
    annee: int,
    codes_departements: list[str],
    exclusions: list[str] | None = None,
) -> pd.DataFrame:
    """Trouve le sport dominant de chaque département demandé."""
    donnees = donnees_departements(annee)
    donnees = donnees.loc[donnees["code_departement"].isin(codes_departements)]

    if exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]

    if donnees.empty:
        return donnees

    indices = donnees.groupby("code_departement")["licences"].idxmax()

    return donnees.loc[indices].reset_index(drop=True)