"""Nettoie les données brutes (tables raw_) et crée les tables cleaned_ utilisées par le dashboard."""

import json
import sqlite3

import pandas as pd

import config

# Tranches d'âge communes aux 12 années (celles des fichiers 2012 à 2018)
TRANCHES = ["0_4", "5_9", "10_14", "15_19", "20_29", "30_44", "45_59", "60_74", "75"]

# Format récent (2019 à 2023) : tranches de 5 ans regroupées dans les tranches communes
TRANCHES_RECENTES = {
    "0_4": ["1 à 4 ans"],
    "5_9": ["5 à 9 ans"],
    "10_14": ["10 à 14 ans"],
    "15_19": ["15 à 19 ans"],
    "20_29": ["20 à 24 ans", "25 à 29 ans"],
    "30_44": ["30 à 34 ans", "35 à 39 ans", "40 à 44 ans"],
    "45_59": ["45 à 49 ans", "50 à 54 ans", "55 à 59 ans"],
    "60_74": ["60 à 64 ans", "65 à 69 ans", "70 à 74 ans"],
    "75": ["75 à 79 ans", "80 à 99 ans"],
}

# Colonnes sexe x tranche de la table nettoyée : f_0_4, ..., f_75, h_0_4, ..., h_75
COLONNES_AGE = [f"{sexe}_{tranche}" for sexe in ("f", "h") for tranche in TRANCHES]


def en_entier(colonne: pd.Series) -> pd.Series:
    """Convertit une colonne de texte en nombres entiers (une case vide devient 0)."""
    return pd.to_numeric(colonne, errors="coerce").fillna(0).astype(int)


def nettoyer_format_recent(brut: pd.DataFrame, annee: int) -> pd.DataFrame:
    """Années 2019 à 2023 : colonnes « F - 20 à 24 ans », une ligne par commune et quartier."""
    propre = pd.DataFrame({
        "annee": annee,
        "code_commune": brut["Code Commune"],
        "code_federation": brut["Code"],
        "total": en_entier(brut["Total"]),
    })
    for sexe, lettre in (("f", "F"), ("h", "H")):
        for tranche, libelles in TRANCHES_RECENTES.items():
            colonnes = [f"{lettre} - {libelle}" for libelle in libelles]
            propre[f"{sexe}_{tranche}"] = sum(en_entier(brut[c]) for c in colonnes)
    return propre


def nettoyer_format_ancien(brut: pd.DataFrame, annee: int) -> pd.DataFrame:
    """Années 2012 à 2018 : colonnes « l_20_29_f_2018 », une ligne par commune."""
    colonne_federation = next(c for c in brut.columns if c.startswith("fed_"))
    propre = pd.DataFrame({
        "annee": annee,
        "code_commune": brut[brut.columns[0]].str.zfill(5),  # « 1001 » devient « 01001 »
        "code_federation": brut[colonne_federation],
        "total": en_entier(brut[f"l_{annee}"]),
    })
    for sexe in ("f", "h"):
        for tranche in TRANCHES:
            nom = f"l_{tranche}_{sexe}_{annee}"
            if nom not in brut.columns:  # en 2012, la dernière tranche s'appelle « 75_99 »
                nom = f"l_75_99_{sexe}_{annee}"
            propre[f"{sexe}_{tranche}"] = en_entier(brut[nom])
    return propre


def decouper_2012(brut: pd.DataFrame) -> pd.DataFrame:
    """En 2012, chaque ligne est dans une seule colonne : on la découpe sur « ; »."""
    entete = brut.columns[0].split(";")
    brut = brut[brut.columns[0]].str.split(";", expand=True)
    brut.columns = entete
    return brut


def nettoyer_licences(connexion: sqlite3.Connection, annee: int) -> pd.DataFrame:
    """Une année de licences au format commun : une ligne par commune et par fédération."""
    # Lecture par paquets de 100 000 lignes : une année entière en texte prendrait trop de mémoire.
    paquets = pd.read_sql_query(f'SELECT * FROM "raw_licences_{annee}"', connexion, chunksize=100_000)
    morceaux = []
    for brut in paquets:
        if annee >= 2019:
            morceaux.append(nettoyer_format_recent(brut, annee))
        else:
            if len(brut.columns) == 1:
                brut = decouper_2012(brut)
            morceaux.append(nettoyer_format_ancien(brut, annee))
    propre = pd.concat(morceaux)

    # On écarte les licences sans commune (« NR - Non réparti ») ou avec un code invalide.
    propre = propre[propre["code_commune"].str.len() == 5]
    propre = propre[~propre["code_commune"].str.startswith("NR")]

    # Depuis 2019, une commune peut avoir plusieurs lignes (une par quartier) : on les additionne.
    propre = propre.groupby(["annee", "code_commune", "code_federation"], as_index=False).sum()

    # Département = 2 premiers caractères du code commune (3 pour l'outre-mer : 971, 972...).
    propre.insert(2, "code_departement", propre["code_commune"].str[:2])
    outre_mer = propre["code_commune"].str.startswith("97")
    propre.loc[outre_mer, "code_departement"] = propre.loc[outre_mer, "code_commune"].str[:3]
    return propre


def nettoyer_federations(connexion: sqlite3.Connection) -> pd.DataFrame:
    """Code et nom de chaque fédération (le nom le plus récent), et sa famille selon le code."""
    morceaux = []
    for annee in (2016, 2017, 2018):
        morceaux.append(pd.read_sql_query(
            f'SELECT DISTINCT fed_{annee} AS code, nom_fed AS nom, {annee} AS annee '
            f'FROM "raw_licences_{annee}"', connexion))
    for annee in range(2019, 2024):
        morceaux.append(pd.read_sql_query(
            f'SELECT DISTINCT "Code" AS code, "Fédération" AS nom, {annee} AS annee '
            f'FROM "raw_licences_{annee}"', connexion))
    federations = pd.concat(morceaux).sort_values("annee")
    federations = federations.drop_duplicates("code", keep="last")[["code", "nom"]]
    familles = {"1": "unisport olympique", "2": "unisport non olympique", "4": "multisport",
                "5": "handisport et sport adapté", "6": "scolaire et universitaire"}
    federations["famille"] = federations["code"].str[0].map(familles).fillna("autre")
    return federations


def nettoyer_communes(connexion: sqlite3.Connection) -> pd.DataFrame:
    """Population et codes géographiques des communes, avec les bons types."""
    communes = pd.read_sql_query("SELECT * FROM raw_population", connexion)
    communes = communes.rename(columns={"code": "code_commune", "codeDepartement": "code_departement",
                                        "codeRegion": "code_region"})
    communes["population"] = en_entier(communes["population"])
    return communes


def lire_noms_contours(niveau: str) -> pd.DataFrame:
    """Code et nom des régions ou des départements, lus dans les fichiers de contours."""
    with open(config.DATA_RAW_DIR / f"contours_{niveau}.geojson", encoding="utf-8") as fichier:
        contours = json.load(fichier)
    return pd.DataFrame([zone["properties"] for zone in contours["features"]])[["code", "nom"]]


def creer_resume_departements(connexion: sqlite3.Connection) -> None:
    """Table résumée : licences par année, département et fédération (graphiques rapides)."""
    connexion.execute("DROP TABLE IF EXISTS cleaned_licences_departements")
    colonnes = ", ".join(f"SUM({nom}) AS {nom}" for nom in COLONNES_AGE)
    connexion.execute(
        f"""CREATE TABLE cleaned_licences_departements AS
            SELECT annee, code_departement, code_federation,
                   SUM(total) AS total, {colonnes}
            FROM cleaned_licences
            GROUP BY annee, code_departement, code_federation"""
    )
    connexion.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_annee_dep "
        "ON cleaned_licences_departements (annee, code_departement, code_federation)"
    )
    connexion.commit()


def clean_data() -> None:
    """Crée les tables cleaned_ à partir des tables raw_ de la base."""
    connexion = sqlite3.connect(config.DB_PATH)

    for numero, annee in enumerate(sorted(config.LICENCES)):
        print(f"Nettoyage des licences {annee}")
        licences = nettoyer_licences(connexion, annee)
        licences.to_sql("cleaned_licences", connexion,
                        if_exists="replace" if numero == 0 else "append", index=False)

    creer_resume_departements(connexion)
    nettoyer_federations(connexion).to_sql("cleaned_federations", connexion, if_exists="replace", index=False)
    nettoyer_communes(connexion).to_sql("cleaned_communes", connexion, if_exists="replace", index=False)
    lire_noms_contours("regions").to_sql("cleaned_regions", connexion, if_exists="replace", index=False)
    lire_noms_contours("departements").to_sql("cleaned_departements", connexion, if_exists="replace",
                                              index=False)

    # Index : rend rapides les filtres du dashboard (par année, par fédération, par commune).
    connexion.execute("CREATE INDEX IF NOT EXISTS idx_annee_fed ON cleaned_licences (annee, code_federation)")
    connexion.execute("CREATE INDEX IF NOT EXISTS idx_commune ON cleaned_licences (code_commune)")
    connexion.commit()
    connexion.close()


if __name__ == "__main__":
    clean_data()