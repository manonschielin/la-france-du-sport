"""Indicateurs sportifs : agrégations contrôlées et filtres indépendants de Dash."""

import sqlite3
from functools import lru_cache

import pandas as pd

import config
from src.utils.referentiel import nom_sport

FAMILLES_UNISPORT = ("unisport olympique", "unisport non olympique")


TRANCHES_AGE = ["0_4", "5_9", "10_14", "15_19", "20_29", "30_44", "45_59", "60_74", "75"]
LIBELLES_AGE = ["0-4 ans", "5-9 ans", "10-14 ans", "15-19 ans", "20-29 ans",
                "30-44 ans", "45-59 ans", "60-74 ans", "75 ans et +"]
COLONNES_AGE = [f"{sexe}_{tranche}" for sexe in ("f", "h") for tranche in TRANCHES_AGE]


def colonnes_selectionnees(sexe: str = "tous", tranches: list[str] | None = None) -> list[str]:
    """Colonnes sexe/âge à additionner ; une liste vide d'âges signifie tous les âges."""
    if sexe not in {"tous", "f", "h"}:
        raise ValueError(f"Sexe inconnu : {sexe}")
    ages = TRANCHES_AGE if not tranches else tranches
    if any(age not in TRANCHES_AGE for age in ages):
        raise ValueError("Tranche d'âge inconnue")
    sexes = ("f", "h") if sexe == "tous" else (sexe,)
    return [f"{s}_{age}" for s in sexes for age in ages]


def filtre_actif(sexe: str = "tous", tranches: list[str] | None = None) -> bool:
    """Indique si le calcul doit quitter la colonne total."""
    return sexe != "tous" or bool(tranches)


def expression_licences(sexe: str = "tous", tranches: list[str] | None = None,
                        prefixe: str = "") -> str:
    """Expression SQL sûre : seuls des noms de colonnes constants sont autorisés."""
    if not filtre_actif(sexe, tranches):
        return f"COALESCE({prefixe}total, 0)"
    return " + ".join(f"COALESCE({prefixe}{col}, 0)" for col in colonnes_selectionnees(sexe, tranches))


def compter_lignes(donnees: pd.DataFrame, sexe: str = "tous",
                   tranches: list[str] | None = None) -> pd.Series:
    """Extrait les totaux depuis une table en mémoire, avec ou sans filtres."""
    if not filtre_actif(sexe, tranches):
        return donnees["licences"]
    colonnes = colonnes_selectionnees(sexe, tranches)
    manquantes = set(colonnes) - set(donnees.columns)
    if manquantes:
        raise ValueError("Résumé départemental à reconstruire (colonnes sexe/âge absentes) : "
                         + ", ".join(sorted(manquantes)))
    return donnees[colonnes].fillna(0).sum(axis=1)


def _normaliser_codes(colonne: pd.Series, longueur: int | None = None) -> pd.Series:
    """Garde les codes géographiques comme du texte, avec zéros initiaux si requis."""
    codes = colonne.astype("string").str.strip()
    if longueur is not None:
        codes = codes.str.zfill(longueur)
    return codes


@lru_cache(maxsize=1)
def liste_sports() -> pd.DataFrame:
    """Renvoie les fédérations unisports avec un libellé simplifié."""
    with sqlite3.connect(config.DB_PATH) as connexion:
        sports = pd.read_sql_query(
            """SELECT code, nom FROM cleaned_federations
               WHERE famille IN (?, ?) ORDER BY nom""",
            connexion,
            params=FAMILLES_UNISPORT,
        )
    sports["code"] = sports["code"].astype(str)
    sports["sport"] = sports["nom"].apply(nom_sport)
    return sports.sort_values(["sport", "code"]).reset_index(drop=True)


def liste_sports_uniques() -> pd.DataFrame:
    """Un seul choix par discipline dans le menu d'exclusion."""
    return (
        liste_sports()[["sport"]]
        .drop_duplicates()
        .sort_values("sport")
        .reset_index(drop=True)
    )


def verifier_correspondances_departements(connexion: sqlite3.Connection) -> None:
    """Refuse les départements rattachés à plusieurs régions."""
    conflits = pd.read_sql_query(
        """SELECT code_departement, COUNT(DISTINCT code_region) AS n
           FROM cleaned_communes
           WHERE code_departement IS NOT NULL AND code_region IS NOT NULL
           GROUP BY code_departement
           HAVING COUNT(DISTINCT code_region) > 1""",
        connexion,
    )
    if not conflits.empty:
        codes = ", ".join(conflits["code_departement"].astype(str).tolist()[:10])
        raise ValueError(
            "Correspondance département/région ambiguë dans cleaned_communes : "
            + codes
        )


def _agregation_sql(annee: int, niveau: str, sexe: str = "tous",
                    tranches: list[str] | None = None) -> pd.DataFrame:
    """Charge les licences par fédération et territoire, sans dupliquer les jointures."""
    if niveau not in {"region", "departement"}:
        raise ValueError(f"Échelle inconnue : {niveau}")

    total_sql = expression_licences(sexe, tranches, "l.")
    with sqlite3.connect(config.DB_PATH) as connexion:
        if niveau == "region":
            verifier_correspondances_departements(connexion)
            # Une seule ligne par département dans la table de correspondance.
            sql = f"""
                SELECT d.code_region AS code_zone,
                       l.code_federation, f.nom AS federation,
                       SUM({total_sql}) AS licences
                FROM cleaned_licences AS l
                JOIN (
                    SELECT code_departement, MIN(code_region) AS code_region
                    FROM cleaned_communes
                    WHERE code_departement IS NOT NULL AND code_region IS NOT NULL
                    GROUP BY code_departement
                ) AS d ON l.code_departement = d.code_departement
                JOIN cleaned_federations AS f ON l.code_federation = f.code
                WHERE l.annee = ? AND f.famille IN (?, ?)
                GROUP BY d.code_region, l.code_federation, f.nom
            """
        else:
            sql = f"""
                SELECT l.code_departement AS code_zone,
                       l.code_federation, f.nom AS federation,
                       SUM({total_sql}) AS licences
                FROM cleaned_licences AS l
                JOIN cleaned_federations AS f ON l.code_federation = f.code
                WHERE l.annee = ? AND f.famille IN (?, ?)
                GROUP BY l.code_departement, l.code_federation, f.nom
            """
        donnees = pd.read_sql_query(
            sql, connexion, params=(annee, *FAMILLES_UNISPORT)
        )

    donnees["code_zone"] = _normaliser_codes(
        donnees["code_zone"], 2 if niveau == "region" else None
    )
    donnees["code_federation"] = donnees["code_federation"].astype(str)
    donnees["sport"] = donnees["federation"].apply(nom_sport)
    if filtre_actif(sexe, tranches):
        donnees = donnees.loc[donnees["licences"] > 0].copy()
    return donnees


def _regrouper_sports(donnees: pd.DataFrame, colonne_zone: str) -> pd.DataFrame:
    """Additionne les fédérations partageant un nom de sport sans falsifier leurs codes."""
    return (
        donnees.groupby([colonne_zone, "sport"], as_index=False)["licences"]
        .sum()
    )


@lru_cache(maxsize=20)
def donnees_regions(annee: int) -> pd.DataFrame:
    """Licences par région et par discipline pour une année."""
    donnees = _agregation_sql(annee, "region")
    donnees = donnees.rename(columns={"code_zone": "code_region"})
    return _regrouper_sports(donnees, "code_region")


def _donnees_regions_filtrees(annee: int, sexe: str, tranches: list[str] | None) -> pd.DataFrame:
    if not filtre_actif(sexe, tranches):
        return donnees_regions(annee)
    return _regrouper_sports(
        _agregation_sql(annee, "region", sexe, tranches).rename(columns={"code_zone": "code_region"}),
        "code_region",
    )


def sports_par_region(
    annee: int, exclusions: list[str] | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> pd.DataFrame:
    """Filtre les sports exclus, sans modifier les données mises en cache."""
    donnees = _donnees_regions_filtrees(annee, sexe, tranches)
    if exclusions:
        return donnees.loc[~donnees["sport"].isin(exclusions)].copy()
    return donnees.copy()


def sport_numero_un(
    annee: int, exclusions: list[str] | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> pd.DataFrame:
    """Choisit le sport dominant dans chaque région (tri déterministe si égalité)."""
    donnees = sports_par_region(annee, exclusions, sexe, tranches)
    return (
        donnees.sort_values(["licences", "sport"], ascending=[False, True])
        .drop_duplicates("code_region")
        .reset_index(drop=True)
    )


def classement_region(
    annee: int, code_region: str, exclusions: list[str] | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> pd.DataFrame:
    """Dix sports les plus représentés dans une région."""
    donnees = sports_par_region(annee, exclusions, sexe, tranches)
    region = donnees.loc[donnees["code_region"] == str(code_region).zfill(2)]
    return region.sort_values(
        ["licences", "sport"], ascending=[False, True]
    ).head(10).reset_index(drop=True)


@lru_cache(maxsize=20)
def donnees_departements(annee: int) -> pd.DataFrame:
    """Licences par département et par discipline pour une année."""
    donnees = _agregation_sql(annee, "departement")
    donnees = donnees.rename(columns={"code_zone": "code_departement"})
    return _regrouper_sports(donnees, "code_departement")


def _donnees_departements_filtrees(annee: int, sexe: str, tranches: list[str] | None) -> pd.DataFrame:
    if not filtre_actif(sexe, tranches):
        return donnees_departements(annee)
    return _regrouper_sports(
        _agregation_sql(annee, "departement", sexe, tranches).rename(
            columns={"code_zone": "code_departement"}), "code_departement")


def sport_numero_un_departements(
    annee: int,
    codes_departements: list[str],
    exclusions: list[str] | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> pd.DataFrame:
    """Sport dominant dans les départements demandés, hors exclusions."""
    donnees = _donnees_departements_filtrees(annee, sexe, tranches)
    donnees = donnees.loc[
        donnees["code_departement"].isin(codes_departements)
    ]
    if exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]
    return (
        donnees.sort_values(["licences", "sport"], ascending=[False, True])
        .drop_duplicates("code_departement")
        .reset_index(drop=True)
    )


@lru_cache(maxsize=20)
def donnees_communes(annee: int) -> pd.DataFrame:
    """Licences unisport par commune, sans jointure susceptible de dupliquer les lignes."""
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            """SELECT s.code_commune, s.code_federation,
                      f.nom AS federation, s.licences
               FROM (
                   SELECT code_commune, code_federation, SUM(total) AS licences
                   FROM cleaned_licences
                   WHERE annee = ?
                   GROUP BY code_commune, code_federation
               ) AS s
               JOIN cleaned_federations AS f ON s.code_federation = f.code
               WHERE f.famille IN (?, ?)""",
            connexion, params=(annee, *FAMILLES_UNISPORT),
        )
    donnees["code_commune"] = _normaliser_codes(donnees["code_commune"], 5)
    donnees["sport"] = donnees["federation"].apply(nom_sport)
    return _regrouper_sports(donnees, "code_commune")


def _donnees_communes_filtrees(annee: int, sexe: str, tranches: list[str] | None) -> pd.DataFrame:
    if not filtre_actif(sexe, tranches):
        return donnees_communes(annee)
    expression = expression_licences(sexe, tranches)
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT s.code_commune, s.code_federation, f.nom AS federation, s.licences
                FROM (SELECT code_commune, code_federation,
                             SUM({expression}) AS licences
                      FROM cleaned_licences WHERE annee = ?
                      GROUP BY code_commune, code_federation) AS s
                JOIN cleaned_federations AS f ON f.code = s.code_federation
                WHERE f.famille IN (?, ?)""",
            connexion, params=(annee, *FAMILLES_UNISPORT),
        )
    donnees["code_commune"] = _normaliser_codes(donnees["code_commune"], 5)
    donnees["sport"] = donnees["federation"].apply(nom_sport)
    donnees = donnees.loc[donnees["licences"] > 0]
    return _regrouper_sports(donnees, "code_commune")


def sports_par_commune(annee: int, code_commune: str,
                      exclusions: list[str] | None = None,
                      sexe: str = "tous", tranches: list[str] | None = None) -> pd.DataFrame:
    """Sports d'une commune, en respectant les exclusions."""
    donnees = _donnees_communes_filtrees(annee, sexe, tranches)
    donnees = donnees.loc[donnees["code_commune"] == str(code_commune)]
    if exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]
    return donnees.copy()


def sport_numero_un_communes(annee: int, codes_communes: list[str],
                             exclusions: list[str] | None = None,
                             sexe: str = "tous", tranches: list[str] | None = None) -> pd.DataFrame:
    """Sport dominant de chaque commune affichée uniquement."""
    donnees = _donnees_communes_filtrees(annee, sexe, tranches)
    donnees = donnees.loc[donnees["code_commune"].isin(codes_communes)]
    if exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]
    return (donnees.sort_values(["licences", "sport"], ascending=[False, True])
            .drop_duplicates("code_commune").reset_index(drop=True))


def classement_commune(annee: int, code_commune: str,
                       exclusions: list[str] | None = None,
                       sexe: str = "tous", tranches: list[str] | None = None) -> pd.DataFrame:
    """Dix sports les plus représentés dans une commune."""
    return (sports_par_commune(annee, code_commune, exclusions, sexe, tranches)
            .sort_values(["licences", "sport"], ascending=[False, True])
            .head(10).reset_index(drop=True))


def classement_departement(annee: int, code_departement: str,
                           exclusions: list[str] | None = None,
                           sexe: str = "tous", tranches: list[str] | None = None) -> pd.DataFrame:
    """Dix sports les plus représentés dans un département."""
    donnees = _donnees_departements_filtrees(annee, sexe, tranches)
    donnees = donnees.loc[donnees["code_departement"] == str(code_departement)]
    if exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]
    return (donnees.sort_values(["licences", "sport"], ascending=[False, True])
            .head(10).reset_index(drop=True))


@lru_cache(maxsize=1)
def resume_departements() -> pd.DataFrame:
    """Résumé historique départemental ; supporte les anciennes tables pour les tests sans filtres."""
    with sqlite3.connect(config.DB_PATH) as connexion:
        colonnes = {ligne[1] for ligne in connexion.execute(
            'PRAGMA table_info("cleaned_licences_departements")')}
        extras = ", ".join(f"r.{col}" for col in COLONNES_AGE if col in colonnes)
        donnees = pd.read_sql_query(
            f"""SELECT r.annee, r.code_departement, d.code_region,
                       f.nom AS federation, r.total AS licences
                       {',' + extras if extras else ''}
                FROM cleaned_licences_departements AS r
                JOIN cleaned_federations AS f ON r.code_federation = f.code
                LEFT JOIN (
                    SELECT code_departement, MIN(code_region) AS code_region
                    FROM cleaned_communes GROUP BY code_departement
                ) AS d ON r.code_departement = d.code_departement
                WHERE f.famille IN (?, ?)""",
            connexion, params=FAMILLES_UNISPORT,
        )
    donnees["sport"] = donnees["federation"].apply(nom_sport)
    return donnees


@lru_cache(maxsize=50)
def licences_commune(code_commune: str) -> pd.DataFrame:
    """Licences d'une commune par année et sport, arrondissements inclus."""
    codes = codes_licences_commune(code_commune)
    marqueurs = ", ".join("?" for _ in codes)
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT l.annee, f.nom AS federation, SUM(l.total) AS licences
                FROM cleaned_licences AS l
                JOIN cleaned_federations AS f ON l.code_federation = f.code
                WHERE l.code_commune IN ({marqueurs}) AND f.famille IN (?, ?)
                GROUP BY l.annee, f.nom""",
            connexion,
            params=(*codes, *FAMILLES_UNISPORT),
        )
    donnees["sport"] = donnees["federation"].apply(nom_sport)
    return donnees


def licences_commune_filtrees(code_commune: str, sexe: str, tranches: list[str] | None) -> pd.DataFrame:
    """Série communale filtrée par âge et sexe, en regroupant les arrondissements."""
    codes = codes_licences_commune(code_commune)
    marqueurs = ", ".join("?" for _ in codes)
    expression = expression_licences(sexe, tranches, "l.")
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT l.annee, f.nom AS federation, SUM({expression}) AS licences
                FROM cleaned_licences AS l
                JOIN cleaned_federations AS f ON l.code_federation = f.code
                WHERE l.code_commune IN ({marqueurs}) AND f.famille IN (?, ?)
                GROUP BY l.annee, f.nom""",
            connexion, params=(*codes, *FAMILLES_UNISPORT),
        )
    donnees["sport"] = donnees["federation"].apply(nom_sport)
    return donnees


def licences_par_annee(
    niveau: str,
    code: str | None = None,
    exclusions: list[str] | None = None,
    sport: str | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> pd.DataFrame:
    """Licences par année et par territoire, éventuellement limitées à un sport."""
    if niveau == "commune":
        donnees = (licences_commune_filtrees(code, sexe, tranches)
                   if filtre_actif(sexe, tranches) else licences_commune(code))
    else:
        donnees = resume_departements()
        if niveau == "region":
            donnees = donnees.loc[donnees["code_region"] == code]
        elif niveau == "departement":
            donnees = donnees.loc[donnees["code_departement"] == code]

    if sport:
        # Le sport analysé reste prioritaire sur les exclusions générales.
        donnees = donnees.loc[donnees["sport"] == sport]
    elif exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]

    if niveau != "commune" and filtre_actif(sexe, tranches):
        donnees = donnees.copy()
        donnees["licences"] = compter_lignes(donnees, sexe, tranches)
    resultat = donnees.groupby("annee", as_index=False)["licences"].sum()
    if filtre_actif(sexe, tranches):
        resultat = resultat.loc[resultat["licences"] > 0]
    return resultat


# En dessous de ce nombre d'habitants, un seul licencié fausse le taux : on ne le calcule pas.
POPULATION_MINIMUM = 200


def code_ville(code_commune: str) -> str:
    """Remplace un code d'arrondissement par celui de sa ville (75115 -> 75056)."""
    code = str(code_commune)
    if "75101" <= code <= "75120":
        return "75056"  # Paris
    if "69381" <= code <= "69389":
        return "69123"  # Lyon
    if "13201" <= code <= "13216":
        return "13055"  # Marseille
    return code


@lru_cache(maxsize=3)
def populations(niveau: str) -> pd.DataFrame:
    """Population par territoire, en rattachant les arrondissements aux villes."""
    colonne = {"region": "code_region", "departement": "code_departement",
               "commune": "code_commune"}[niveau]
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"SELECT {colonne} AS code, population FROM cleaned_communes",
            connexion,
        )
    donnees["code"] = donnees["code"].astype(str)
    donnees["population"] = pd.to_numeric(
        donnees["population"], errors="coerce"
    )
    if niveau == "commune":
        # Si la ville et ses arrondissements coexistent, préférer le total ville.
        villes = {"75056", "69123", "13055"}
        presents = set(donnees.loc[donnees["code"].isin(villes), "code"])
        donnees["code_origine"] = donnees["code"]
        donnees["code"] = donnees["code"].map(code_ville)
        donnees = donnees.loc[
            ~(
                donnees["code"].isin(presents)
                & (donnees["code_origine"] != donnees["code"])
            )
        ]
    return donnees.groupby("code", as_index=False)["population"].sum(min_count=1)


def codes_federations(sport: str) -> list[str]:
    """Codes des fédérations regroupées sous un même nom de sport (ex. : les deux de judo)."""
    sports = liste_sports()
    return sports.loc[sports["sport"] == sport, "code"].tolist()


@lru_cache(maxsize=50)
def licences_sport_communes(annee: int, sport: str) -> pd.DataFrame:
    """Licences d'un sport dans chaque commune pour une année (arrondissements regroupés)."""
    codes = codes_federations(sport)
    if not codes:
        return pd.DataFrame(columns=["code", "licences"])
    marqueurs = ", ".join("?" * len(codes))
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT code_commune AS code, SUM(total) AS licences
                FROM cleaned_licences
                WHERE annee = ? AND code_federation IN ({marqueurs})
                GROUP BY code_commune""",
            connexion,
            params=(annee, *codes),
        )
    donnees["code"] = donnees["code"].apply(code_ville)
    return donnees.groupby("code", as_index=False)["licences"].sum()


def licences_sport_communes_filtrees(
    annee: int, sport: str, sexe: str, tranches: list[str] | None,
) -> pd.DataFrame:
    """Licences du sport par commune pour les colonnes sexe/âge sélectionnées."""
    codes = codes_federations(sport)
    if not codes:
        return pd.DataFrame(columns=["code", "licences"])
    expression = expression_licences(sexe, tranches)
    marqueurs = ", ".join("?" * len(codes))
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT code_commune AS code, SUM({expression}) AS licences
                FROM cleaned_licences WHERE annee = ?
                AND code_federation IN ({marqueurs}) GROUP BY code_commune""",
            connexion, params=(annee, *codes),
        )
    donnees["code"] = donnees["code"].map(code_ville)
    return donnees.groupby("code", as_index=False)["licences"].sum()


def licences_pour_1000(annee: int, sport: str, niveau: str,
                       sexe: str = "tous", tranches: list[str] | None = None) -> pd.DataFrame:
    """Licences du sport pour 1 000 habitants, codes sans données compris.

    Le taux est absent si aucune licence n'est renseignée, si la population
    manque ou si la commune compte moins de 200 habitants.
    """
    if niveau not in {"region", "departement", "commune"}:
        raise ValueError(f"Échelle inconnue : {niveau}")
    if niveau == "commune":
        licences = (licences_sport_communes_filtrees(annee, sport, sexe, tranches)
                    if filtre_actif(sexe, tranches) else licences_sport_communes(annee, sport))
    else:
        resume = resume_departements()
        resume = resume.loc[(resume["annee"] == annee) & (resume["sport"] == sport)].copy()
        if filtre_actif(sexe, tranches):
            resume["licences"] = compter_lignes(resume, sexe, tranches)
        colonne = "code_region" if niveau == "region" else "code_departement"
        licences = (resume.groupby(colonne, as_index=False)["licences"].sum()
                    .rename(columns={colonne: "code"}))

    licences = licences.copy()
    population = populations(niveau).copy()
    licences["code"] = licences["code"].astype(str)
    population["code"] = population["code"].astype(str)
    if niveau == "region":
        licences["code"] = licences["code"].str.zfill(2)
        population["code"] = population["code"].str.zfill(2)

    donnees = population.merge(licences, on="code", how="outer")
    donnees["taux"] = (donnees["licences"] / donnees["population"] * 1000).round(1)
    invalide = (donnees["population"].isna()
                | (donnees["population"] <= 0)
                | donnees["licences"].isna())
    if niveau == "commune":
        invalide |= donnees["population"] < POPULATION_MINIMUM
    donnees.loc[invalide, "taux"] = float("nan")
    return donnees.sort_values("taux", ascending=False, na_position="last").reset_index(drop=True)


def _ajouter_sports(donnees: pd.DataFrame) -> pd.DataFrame:
    """Ajoute le nom du sport et ne garde que les fédérations unisport."""
    sports = liste_sports()[["code", "sport"]].rename(columns={"code": "code_federation"})
    return donnees.merge(sports, on="code_federation", how="inner")


@lru_cache(maxsize=12)
def ages_departements(annee: int) -> pd.DataFrame:
    """Licences par département, fédération, sexe et tranche d'âge pour une année."""
    sommes = ", ".join(f"SUM({colonne}) AS {colonne}" for colonne in COLONNES_AGE)
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT a.*, d.code_region
                FROM (
                    SELECT code_departement, code_federation, {sommes}
                    FROM cleaned_licences
                    WHERE annee = ?
                    GROUP BY code_departement, code_federation
                ) AS a
                LEFT JOIN (
                    SELECT code_departement, MIN(code_region) AS code_region
                    FROM cleaned_communes
                    GROUP BY code_departement
                ) AS d ON a.code_departement = d.code_departement""",
            connexion,
            params=(annee,),
        )
    return _ajouter_sports(donnees)


def codes_licences_commune(code_commune: str) -> list[str]:
    """Codes à chercher pour une commune : Paris, Lyon et Marseille ont leurs arrondissements."""
    if code_commune == "75056":
        return [code_commune] + [f"751{n:02d}" for n in range(1, 21)]
    if code_commune == "69123":
        return [code_commune] + [f"6938{n}" for n in range(1, 10)]
    if code_commune == "13055":
        return [code_commune] + [f"132{n:02d}" for n in range(1, 17)]
    return [code_commune]


@lru_cache(maxsize=50)
def ages_commune(annee: int, code_commune: str) -> pd.DataFrame:
    """Licences d'une commune par fédération, sexe et tranche d'âge pour une année."""
    codes = codes_licences_commune(code_commune)
    sommes = ", ".join(f"SUM({colonne}) AS {colonne}" for colonne in COLONNES_AGE)
    marqueurs = ", ".join("?" * len(codes))
    with sqlite3.connect(config.DB_PATH) as connexion:
        donnees = pd.read_sql_query(
            f"""SELECT code_federation, {sommes}
                FROM cleaned_licences INDEXED BY idx_commune
                WHERE code_commune IN ({marqueurs}) AND annee = ?
                GROUP BY code_federation""",
            connexion,
            params=(*codes, annee),
        )
    return _ajouter_sports(donnees)


def pyramide_ages(
    annee: int,
    niveau: str,
    code: str | None = None,
    sport: str | None = None,
    exclusions: list[str] | None = None,
    sexe: str = "tous", tranches: list[str] | None = None,
) -> pd.DataFrame:
    """Nombre de licences par tranche d'âge, femmes et hommes, pour la zone choisie."""
    if niveau == "commune":
        donnees = ages_commune(annee, code)
    else:
        donnees = ages_departements(annee)
        if niveau == "region":
            donnees = donnees.loc[donnees["code_region"] == code]
        elif niveau == "departement":
            donnees = donnees.loc[donnees["code_departement"] == code]

    if sport:
        donnees = donnees.loc[donnees["sport"] == sport]
    elif exclusions:
        donnees = donnees.loc[~donnees["sport"].isin(exclusions)]

    colonnes_selectionnees(sexe, tranches)  # Vérification des filtres.
    sommes = donnees[COLONNES_AGE].sum()
    return pd.DataFrame({
        "tranche": LIBELLES_AGE,
        "femmes": [int(sommes[f"f_{tranche}"]) for tranche in TRANCHES_AGE],
        "hommes": [int(sommes[f"h_{tranche}"]) for tranche in TRANCHES_AGE],
    })


def chiffres_cles() -> dict[str, int | float | str]:
    """Chiffres clés de la dernière année disponible, pour la page d'accueil."""
    donnees = resume_departements()
    par_annee = donnees.groupby("annee")["licences"].sum()
    derniere_annee = int(par_annee.index.max())
    annee = donnees.loc[donnees["annee"] == derniere_annee]

    femmes = annee[[c for c in COLONNES_AGE if c.startswith("f_")]].sum().sum()
    hommes = annee[[c for c in COLONNES_AGE if c.startswith("h_")]].sum().sum()

    return {
        "annee": derniere_annee,
        "licences": int(par_annee[derniere_annee]),
        "part_femmes": round(100 * femmes / (femmes + hommes), 1),
        "sport_numero_un": str(annee.groupby("sport")["licences"].sum().idxmax()),
        "nb_sports": int(annee["sport"].nunique()),
        "annee_record": int(par_annee.idxmax()),
    }