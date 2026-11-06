"""Calculs nationaux des profils démographiques des licences unisports."""

from functools import lru_cache

import pandas as pd

from src.utils.indicateurs import (
    COLONNES_AGE,
    LIBELLES_AGE,
    TRANCHES_AGE,
    resume_departements,
)

SEUIL_EFFECTIF = 10_000
NB_SPORTS_CHALEUR = 15


@lru_cache(maxsize=1)
def donnees_profils() -> pd.DataFrame:
    """Regroupe les 18 colonnes sexe/âge par année et discipline en France."""
    donnees = resume_departements()
    manquantes = sorted(set(COLONNES_AGE) - set(donnees.columns))
    if manquantes:
        raise ValueError(
            "Le résumé départemental ne contient pas les colonnes sexe/âge : "
            + ", ".join(manquantes)
            + ". Exécuter uv run python -m src.utils.rebuild_resume."
        )
    donnees = donnees[["annee", "sport", *COLONNES_AGE]].copy()
    donnees[COLONNES_AGE] = donnees[COLONNES_AGE].apply(pd.to_numeric, errors="coerce").fillna(0)
    resultat = donnees.groupby(["annee", "sport"], as_index=False)[COLONNES_AGE].sum()
    resultat["annee"] = resultat["annee"].astype(int)
    resultat["femmes"] = resultat[[f"f_{age}" for age in TRANCHES_AGE]].sum(axis=1)
    resultat["hommes"] = resultat[[f"h_{age}" for age in TRANCHES_AGE]].sum(axis=1)
    resultat["renseignes"] = resultat["femmes"] + resultat["hommes"]
    return resultat


def parts_femmes(annee: int = 2023, seuil: int = SEUIL_EFFECTIF) -> pd.DataFrame:
    """Part féminine parmi les licences avec sexe/âge renseignés, par sport."""
    source = donnees_profils()
    resultat = source.loc[(source["annee"] == annee) & (source["renseignes"] >= seuil)].copy()
    resultat = resultat.loc[resultat["renseignes"] > 0]
    resultat["part_femmes"] = 100 * resultat["femmes"] / resultat["renseignes"]
    return resultat.sort_values(["part_femmes", "sport"], ascending=[False, True]).reset_index(drop=True)


def repartition_ages(annee: int = 2023, nombre: int = NB_SPORTS_CHALEUR) -> pd.DataFrame:
    """Distribution (%) par âge des principales disciplines, sans biais de taille."""
    source = donnees_profils()
    courants = source.loc[(source["annee"] == annee) & (source["renseignes"] > 0)]
    courants = courants.sort_values("renseignes", ascending=False).head(nombre).copy()
    lignes = []
    for _, ligne in courants.iterrows():
        for tranche, etiquette in zip(TRANCHES_AGE, LIBELLES_AGE):
            licences = ligne[f"f_{tranche}"] + ligne[f"h_{tranche}"]
            lignes.append({
                "sport": ligne["sport"], "tranche": etiquette,
                "licences": int(licences),
                "pourcentage": 100 * licences / ligne["renseignes"],
            })
    return pd.DataFrame(lignes, columns=["sport", "tranche", "licences", "pourcentage"])


def licences_par_tranche_age(annee: int = 2023) -> pd.DataFrame:
    """Compte les licences renseignées de chaque tranche d'âge en France.

    Les neuf catégories sont de largeurs inégales : ce sont des effectifs,
    et non des taux de pratique par personne ou par année d'âge.
    """
    donnees = donnees_profils()
    selection = donnees.loc[donnees["annee"] == annee]
    lignes = []
    for tranche, libelle in zip(TRANCHES_AGE, LIBELLES_AGE):
        femmes = int(selection[f"f_{tranche}"].sum())
        hommes = int(selection[f"h_{tranche}"].sum())
        lignes.append({
            "tranche": libelle,
            "licences": femmes + hommes,
            "femmes": femmes,
            "hommes": hommes,
        })
    return pd.DataFrame(lignes)


def evolution_part_femmes(sports: list[str]) -> pd.DataFrame:
    """Séries de part féminine par sport, sans inventer les années absentes."""
    if not 1 <= len(sports) <= 5:
        raise ValueError("Choisir entre un et cinq sports.")
    source = donnees_profils()
    resultat = source.loc[source["sport"].isin(sports) & (source["renseignes"] > 0)].copy()
    resultat["part_femmes"] = 100 * resultat["femmes"] / resultat["renseignes"]
    return resultat[["annee", "sport", "part_femmes", "renseignes"]].sort_values(["sport", "annee"])


def sports_disponibles() -> list[str]:
    """Sports possédant des données démographiques sur au moins une année."""
    source = donnees_profils()
    return sorted(source.loc[source["renseignes"] > 0, "sport"].unique().tolist())


def sports_par_defaut(annee: int = 2023) -> list[str]:
    """Trois disciplines majeures ayant des informations démographiques."""
    source = donnees_profils()
    selection = source.loc[(source["annee"] == annee) & (source["renseignes"] > 0)]
    return selection.nlargest(3, "renseignes")["sport"].tolist()
