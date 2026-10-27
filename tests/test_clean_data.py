
"""Vérifications simples de l'état des données nettoyées (après clean_data)."""
# Pour exécuter : uv run python -m tests.test_clean_data

import sqlite3
import pandas as pd
import config


def afficher_tables(connexion: sqlite3.Connection) -> None:
    """Liste les tables nettoyées et leur nombre de lignes."""
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'cleaned_%'",
        connexion
    )
    for table in tables["name"]:
        nb = pd.read_sql_query(
            f'SELECT COUNT(*) AS n FROM "{table}"', connexion
        )["n"][0]
        print(table, ":", nb, "lignes")


def afficher_apercu(connexion: sqlite3.Connection, table: str) -> None:
    """Affiche les 5 premières lignes d'une table."""
    print(pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT 5', connexion))


def afficher_colonnes(connexion: sqlite3.Connection, table: str) -> None:
    """Affiche le nombre et la liste des colonnes d'une table."""
    colonnes = pd.read_sql_query(
        f'PRAGMA table_info("{table}")', connexion
    )["name"]
    print(table, ":", len(colonnes), "colonnes")
    for colonne in colonnes:
        print("  -", colonne)


def verifier_annees(connexion: sqlite3.Connection) -> None:
    """Affiche le nombre de lignes de licences pour chaque année."""
    resultat = pd.read_sql_query(
        "SELECT annee, COUNT(*) AS nb_lignes "
        "FROM cleaned_licences GROUP BY annee ORDER BY annee",
        connexion
    )
    print(resultat.to_string(index=False))


def verifier_valeurs_manquantes(connexion: sqlite3.Connection) -> None:
    """Vérifie les valeurs manquantes dans les colonnes principales."""
    tables = ["cleaned_licences", "cleaned_federations", "cleaned_communes"]

    for table in tables:
        donnees = pd.read_sql_query(f'SELECT * FROM "{table}"', connexion)
        print(table, ":")
        print(donnees.isnull().sum().to_string())


def verifier_doublons(connexion: sqlite3.Connection) -> None:
    """Vérifie qu'il n'y a pas plusieurs lignes pour une même année, commune et fédération."""
    doublons = pd.read_sql_query(
        "SELECT annee, code_commune, code_federation, COUNT(*) AS n "
        "FROM cleaned_licences "
        "GROUP BY annee, code_commune, code_federation "
        "HAVING COUNT(*) > 1",
        connexion
    )
    print("Nombre de doublons :", len(doublons))


if __name__ == "__main__":
    connexion = sqlite3.connect(config.DB_PATH)

    print("\n--- Tables nettoyées ---")
    afficher_tables(connexion)

    print("\n--- Aperçu des licences ---")
    afficher_apercu(connexion, "cleaned_licences")

    print("\n--- Colonnes des licences ---")
    afficher_colonnes(connexion, "cleaned_licences")

    print("\n--- Aperçu des fédérations ---")
    afficher_apercu(connexion, "cleaned_federations")

    print("\n--- Aperçu des communes ---")
    afficher_apercu(connexion, "cleaned_communes")

    print("\n--- Aperçu des régions ---")
    afficher_apercu(connexion, "cleaned_regions")

    print("\n--- Aperçu des départements ---")
    afficher_apercu(connexion, "cleaned_departements")

    print("\n--- Nombre de lignes par année ---")
    verifier_annees(connexion)

    print("\n--- Valeurs manquantes ---")
    verifier_valeurs_manquantes(connexion)

    print("\n--- Vérification des doublons ---")
    verifier_doublons(connexion)

    connexion.close()
