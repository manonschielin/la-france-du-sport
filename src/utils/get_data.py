"""Récupère les données brutes et les stocke sans modification (data/raw + SQLite)."""


import csv
import json
import sqlite3
import urllib.request
from pathlib import Path


import config




def telecharger(url: str, chemin: Path) -> None:
    """Enregistre le fichier d'une URL dans data/raw (s'il n'y est pas déjà)."""
    if not chemin.exists():
        print(f"Téléchargement de {chemin.name}")
        requete = urllib.request.Request(url)
        requete.add_header("User-Agent", "Mozilla/5.0")
        chemin.write_bytes(urllib.request.urlopen(requete).read())




def inserer(connexion: sqlite3.Connection, table: str, colonnes: list[str], lignes) -> None:
    """Crée une table SQLite (colonnes en texte) et y insère les lignes."""
    definition = ", ".join('"' + c + '" TEXT' for c in colonnes)
    marqueurs = ", ".join("?" * len(colonnes))
    connexion.execute(f'DROP TABLE IF EXISTS "{table}"')
    connexion.execute(f'CREATE TABLE "{table}" ({definition})')
    connexion.executemany(f'INSERT INTO "{table}" VALUES ({marqueurs})', lignes)
    connexion.commit()




def recuperer_licences(connexion: sqlite3.Connection) -> None:
    """Une table raw_licences_AAAA par année (les colonnes changent selon les années)."""
    for annee, (url, sep, encodage) in config.LICENCES.items():
        chemin = config.DATA_RAW_DIR / f"licences_{annee}.csv"
        telecharger(url, chemin)
        with open(chemin, encoding=encodage, newline="") as fichier:
            lecteur = csv.reader(fichier, delimiter=sep)
            colonnes = next(lecteur)  # la première ligne contient les noms des colonnes
            inserer(connexion, f"raw_licences_{annee}", colonnes, lecteur)




def recuperer_population(connexion: sqlite3.Connection) -> None:
    """Population et codes géographiques des communes, depuis l'API (réponse JSON)."""
    chemin = config.DATA_RAW_DIR / "population.json"
    telecharger(config.POPULATION_URL, chemin)
    communes = json.loads(chemin.read_text(encoding="utf-8"))
    colonnes = list(communes[0])
    lignes = [[commune.get(c) for c in colonnes] for commune in communes]
    inserer(connexion, "raw_population", colonnes, lignes)




def recuperer_contours() -> None:
    """Contours des régions, départements et communes (fichiers GeoJSON pour la carte)."""
    for niveau, url in config.CONTOURS.items():
        telecharger(url, config.DATA_RAW_DIR / f"contours_{niveau}.geojson")




def get_data() -> None:
    """Récupère toutes les sources de données."""
    config.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(config.DB_PATH)
    recuperer_licences(connexion)
    recuperer_population(connexion)
    recuperer_contours()
    connexion.close()




if __name__ == "__main__":
    get_data()
