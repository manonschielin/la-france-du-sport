"""Indicateurs nationaux de la page Tendances (fédérations unisports)."""

from functools import lru_cache

import pandas as pd

from src.utils.indicateurs import resume_departements

ANNEES = tuple(range(2012, 2024))
SEUIL_LICENCES = 10_000


@lru_cache(maxsize=1)
def licences_nationales() -> pd.DataFrame:
    """Une ligne par année et sport, en conservant les années réellement observées."""
    donnees = resume_departements()
    resultat = (donnees.groupby(["annee", "sport"], as_index=False)[["licences"]]
                .sum())
    resultat["annee"] = pd.to_numeric(resultat["annee"], errors="raise").astype(int)
    resultat["licences"] = pd.to_numeric(resultat["licences"], errors="raise")
    return resultat.sort_values(["annee", "sport"]).reset_index(drop=True)


def variations(annee_debut: int = 2012, annee_fin: int = 2023,
               seuil: int = SEUIL_LICENCES) -> pd.DataFrame:
    """Variation (%) des sports présents aux deux dates et assez grands au départ."""
    if annee_debut >= annee_fin:
        raise ValueError("L'année de départ doit précéder celle d'arrivée.")
    source = licences_nationales()
    debut = source.loc[source["annee"] == annee_debut, ["sport", "licences"]]
    fin = source.loc[source["annee"] == annee_fin, ["sport", "licences"]]
    valeurs = debut.merge(fin, on="sport", suffixes=("_debut", "_fin"))
    valeurs = valeurs.loc[valeurs["licences_debut"] >= seuil].copy()
    valeurs["variation"] = (100 * (valeurs["licences_fin"] - valeurs["licences_debut"])
                            / valeurs["licences_debut"])
    return valeurs.sort_values("variation", ascending=False).reset_index(drop=True)


def effet_covid(seuil: int = SEUIL_LICENCES, nombre: int = 12) -> pd.DataFrame:
    """Comparaison 2019→2021 et 2021→2023 des grands sports observés trois fois."""
    source = licences_nationales()
    donnees = source.loc[source["annee"].isin((2019, 2021, 2023))]
    large = donnees.pivot(index="sport", columns="annee", values="licences")
    if not {2019, 2021, 2023}.issubset(large.columns):
        return pd.DataFrame(columns=["sport", "variation_2019_2021", "variation_2021_2023"])
    large = large.dropna(subset=[2019, 2021, 2023])
    large = large.loc[(large[2019] >= seuil) & (large[2021] > 0)]
    large = large.loc[large[2019].nlargest(nombre).index].copy()
    large["variation_2019_2021"] = 100 * (large[2021] / large[2019] - 1)
    large["variation_2021_2023"] = 100 * (large[2023] / large[2021] - 1)
    return large.reset_index()[["sport", "variation_2019_2021", "variation_2021_2023"]]


def sports_comparables() -> list[str]:
    """Sports disposant de séries utilisables sur au moins deux années."""
    source = licences_nationales()
    return sorted(source.groupby("sport")["annee"].nunique().loc[lambda x: x >= 2].index.tolist())


def sports_par_defaut() -> list[str]:
    """Trois sports de grande taille et suivis sur toutes les années, si possible."""
    source = licences_nationales()
    nb_annees = source["annee"].nunique()
    disponibles = source.groupby("sport")["annee"].nunique()
    complets = disponibles.index[disponibles == nb_annees]
    recents = source.loc[(source["annee"] == source["annee"].max())
                         & source["sport"].isin(complets)]
    choix = recents.sort_values("licences", ascending=False)["sport"].head(3).tolist()
    if len(choix) < 2:
        choix = (source.loc[source["annee"] == source["annee"].max()]
                .sort_values("licences", ascending=False)["sport"].head(3).tolist())
    return choix


def evolution_sports(sports: list[str]) -> pd.DataFrame:
    """Séries réelles (absence d'année = donnée manquante, jamais zéro ajouté)."""
    if not 2 <= len(sports) <= 5:
        raise ValueError("Sélectionner entre deux et cinq sports.")
    return licences_nationales().loc[lambda d: d["sport"].isin(sports)].copy()
