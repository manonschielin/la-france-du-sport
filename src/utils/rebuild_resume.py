"""Reconstruit uniquement le résumé départemental depuis cleaned_licences.

Lancer depuis la racine : uv run python -m src.utils.rebuild_resume
"""

import sqlite3

import config
from src.utils.clean_data import COLONNES_AGE, creer_resume_departements


def main() -> None:
    """Actualise la table historique sans télécharger ni nettoyer les sources."""
    if not config.DB_PATH.is_file():
        raise FileNotFoundError(f"Base SQLite absente : {config.DB_PATH}")
    with sqlite3.connect(config.DB_PATH) as connexion:
        tables = {row[0] for row in connexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if "cleaned_licences" not in tables:
            raise RuntimeError("Table cleaned_licences absente : lancer le nettoyage initial")
        colonnes = {row[1] for row in connexion.execute('PRAGMA table_info("cleaned_licences")')}
        manquantes = set(COLONNES_AGE) - colonnes
        if manquantes:
            raise RuntimeError(f"Colonnes sexe/âge absentes : {sorted(manquantes)}")
        creer_resume_departements(connexion)
        lignes = connexion.execute(
            "SELECT COUNT(*) FROM cleaned_licences_departements"
        ).fetchone()[0]
    print(f"Résumé départemental reconstruit : {lignes} lignes, 18 colonnes sexe/âge.")


if __name__ == "__main__":
    main()
