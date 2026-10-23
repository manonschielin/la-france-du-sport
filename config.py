"""Configuration : chemins et URL des sources de données."""


from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DB_PATH = ROOT_DIR / "data" / "cleaned" / "sport.db"


_LIC = ("https://static.data.gouv.fr/resources/donnees-geocodees-issues-du-recensement-des-licences-"
        "et-clubs-aupres-des-federations-sportives-agreees-par-le-ministere-charge-des-sports")
_ANCIEN = ("https://static.data.gouv.fr/resources/recensement-des-licences-et-clubs-aupres-des-"
           "federations-sportives-agreees-par-le-ministere-charge-d")


# Licences sportives par commune et par fédération : année -> (url, séparateur)
LICENCES = {
    2023: (f"{_LIC}/20251229-163107/lic-data-2023.csv", ";", "utf-8-sig"),
    2022: (f"{_LIC}/20241230-162428/lic-data-2022.csv", ";", "utf-8-sig"),
    2021: (f"{_LIC}/20231207-134903/lic-data-2021.csv", ";", "utf-8-sig"),
    2020: (f"{_LIC}/20231207-134516/lic-data-2020.csv", ";", "utf-8-sig"),
    2019: (f"{_LIC}/20231207-134205/lic-data-2019.csv", ";", "utf-8-sig"),
    2018: (f"{_LIC}/20220217-115513/lic-data-2018.csv", ";", "cp1252"),
    2017: (f"{_LIC}/20201029-165909/lic-data-2017.csv", ";", "cp1252"),
    2016: (f"{_LIC}/20201030-145527/lic-data-2016.csv", ";", "cp1252"),
    2015: (f"{_ANCIEN}/20180131-163516/Licences_2015.csv", ",", "cp1252"),
    2014: (f"{_ANCIEN}/20161215-152726/Licences_2014.csv", ",", "cp1252"),
    2013: (f"{_ANCIEN}/20160826-142541/Licences_2013.csv", ";", "utf-8"),
    2012: ("https://static.data.gouv.fr/resources/licences_2012.csv", ";", "utf-8"),
}


# Population et codes département / région de chaque commune (API Découpage administratif)
POPULATION_URL = ("https://geo.api.gouv.fr/communes"
                  "?fields=code,nom,population,codeDepartement,codeRegion&format=json")


# Contours administratifs 2025 (GeoJSON)
_GEO = "https://object.data.gouv.fr/contours-administratifs/2025/geojson"
CONTOURS = {
    "regions": f"{_GEO}/regions-1000m.geojson",
    "departements": f"{_GEO}/departements-1000m.geojson",
    "communes": f"{_GEO}/communes-100m.geojson",
}
