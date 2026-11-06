"""Vérifications simples de l'état des données brutes (après get_data)."""
#pour compiler, éxecuter cette commande : uv run python -m tests.test_get_data

import sqlite3

import pandas as pd

import config


def afficher_tables(connexion: sqlite3.Connection) -> None:
    """Liste les tables de la base et leur nombre de lignes."""
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type = 'table'", connexion)
    for table in tables["name"]:
        nb = pd.read_sql_query(f'SELECT COUNT(*) AS n FROM "{table}"', connexion)["n"][0]
        print(table, ":", nb, "lignes")


def afficher_apercu(connexion: sqlite3.Connection, table: str) -> None:
    """Affiche les 5 premières lignes d'une table."""
    print(pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT 5', connexion))


def afficher_colonnes(connexion: sqlite3.Connection, table: str) -> None:
    """Affiche le nombre et la liste des colonnes d'une table."""
    colonnes = pd.read_sql_query(f'PRAGMA table_info("{table}")', connexion)["name"]
    print(table, ":", len(colonnes), "colonnes")
    for colonne in colonnes:
        print("  -", colonne)


if __name__ == "__main__":
    connexion = sqlite3.connect(config.DB_PATH)
    afficher_tables(connexion)
    afficher_apercu(connexion, "raw_licences_2023")
    afficher_colonnes(connexion, "raw_licences_2019")
    connexion.close()