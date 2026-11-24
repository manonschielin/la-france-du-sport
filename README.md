# La France du sport

Tableau de bord interactif sur **12 ans de licences sportives en France (2012-2023)**, de la région jusqu'à la commune : quel sport domine où, comment la pratique évolue, et qui sont les licenciés.

Projet data du cours Python 2, E4, ESIEE Paris, 2026.
**Auteurs :** Manon SCHIELIN et Thomas QUÉRO.

## Ce que montre le dashboard

| Page | Contenu |
| --- | --- |
| **Accueil** | Présentation du projet et chiffres clés. |
| **Explorer la carte** | Carte du sport dominant par région ; un clic sur une région descend au niveau des départements, puis des communes. Filtres par année, sport, sexe, âge et sports à exclure (par exemple « hors foot »). Évolution du nombre de licences, classement des sports et pyramide des âges du territoire choisi. |
| **Tendances** | Évolution nationale des pratiques entre 2012 et 2023. |
| **Qui fait du sport ?** | Répartition des licences par sexe et par âge. |
| **Répartition des licences** | Histogramme des communes selon leur nombre de licences pour 1 000 habitants. |

## Les données

Toutes les sources sont ouvertes et téléchargées automatiquement au premier lancement :

- **Licences sportives par commune et par fédération** (ministère chargé des Sports, data.gouv.fr), un fichier par année de 2012 à 2023 ;
- **Population et codes département / région** des communes (API Découpage administratif, geo.api.gouv.fr) ;
- **Contours administratifs 2025** des régions, départements et communes (GeoJSON, data.gouv.fr).

## Architecture

```
main.py                  point d'entrée : prépare les données si besoin, puis lance Dash
config.py                chemins et URL des sources
src/
├── utils/
│   ├── get_data.py      téléchargement des données brutes → tables raw_ (SQLite)
│   ├── clean_data.py    nettoyage → tables cleaned_ utilisées par le dashboard
│   ├── indicateurs.py   calculs (sport dominant, taux pour 1 000 habitants, filtres)
│   └── ...              tendances, profils, distribution, couleurs, référentiel
├── components/          carte, classement, évolution, pyramide, filtres, en-tête, navigation
└── pages/               accueil, carte, tendances, profils, répartition
tests/                   tests pytest des calculs et du nettoyage
```

**La chaîne de données :**

1. `get_data.py` télécharge chaque source et la stocke **sans modification** dans `data/raw/` et dans des tables `raw_` d'une base SQLite.
2. `clean_data.py` harmonise les 12 années, qui n'ont pas toutes le même format (séparateurs, encodages UTF-8 ou cp1252, colonnes d'âge et de sexe différentes). Il produit une table `cleaned_licences` (une ligne par année, commune et fédération) et des tables de référence (fédérations, communes, départements, régions).
3. Une **table résumée par département** évite de reparcourir toute la base à chaque clic.

**Quelques choix techniques :**

- **Performance :** les requêtes SQL ont été réécrites (agrégations dans des sous-requêtes, table résumée) : l'affichage d'une région est passé de **32 s à 3,6 s**, et celui des communes de 38 s à 10 s.
- **Arrondissements :** Paris, Lyon et Marseille sont déclarés par arrondissement dans les licences ; ils sont ramenés à leur ville pour ne perdre aucune licence.
- **Foot :** le football arrive en tête dans presque tous les départements ; le filtre « sports à exclure » permet de voir le sport dominant hors foot.

## Lancer le projet

Prérequis : [uv](https://docs.astral.sh/uv/) et Python 3.14.

```bash
git clone https://github.com/manonschielin/la-france-du-sport.git
cd la-france-du-sport
uv sync
uv run python main.py
```

Puis ouvrir http://127.0.0.1:8050 dans un navigateur.

Au premier lancement, les données sont téléchargées puis nettoyées : comptez plusieurs minutes et environ 2,5 Go d'espace disque. Les lancements suivants utilisent directement la base `data/cleaned/sport.db`.

## Qualité du code

```bash
uv run pytest        # tests
uv run ruff check .  # style
uv run mypy .        # types
```

## Outils

Python 3.14 · Dash · Plotly · pandas · SQLite · uv · pytest · ruff · mypy
