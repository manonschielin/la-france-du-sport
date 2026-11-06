
"""Noms et couleurs des disciplines sportives."""

import colorsys
import hashlib
import re
import unicodedata

from src.utils.couleurs import CATEGORIE_1

NOMS_COURTS = {
    "football": "Football",
    "tennis": "Tennis",
    "basketball": "Basketball",
    "basket ball": "Basketball",
    "handball": "Handball",
    "hand ball": "Handball",
    "equitation": "Équitation",
    "judo jujitsu kendo et da": "Judo",
    "judo jujitsu kendo et disciplines associees": "Judo",
    "natation": "Natation",
    "athletisme": "Athlétisme",
    "cyclisme": "Cyclisme",
    "rugby": "Rugby",
    "rugby a xv": "Rugby",
    "gymnastique": "Gymnastique",
    "badminton": "Badminton",
    "volleyball": "Volleyball",
    "volley ball": "Volleyball",
    "golf": "Golf",
    "escrime": "Escrime",
    "tir a l arc": "Tir à l'arc",
    "tennis de table": "Tennis de table",
    "football americain": "Football américain",
}


def normaliser(nom: str) -> str:
    """Normalise un nom pour faciliter les correspondances."""
    sans_accents = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", nom)
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]+", " ", sans_accents.lower()).strip()


def nom_sport(nom_federation: str) -> str:
    """Retourne un nom court tout en conservant les cas inconnus."""
    nom = str(nom_federation or "").strip()

    # Retire les préfixes courants des fédérations.
    nom = re.sub(
        r"^(FF de |FF d'|FF du |FF des |"
        r"Fédération Française de |Fédération Française d'|"
        r"Fédération Française du |Fédération Française des )",
        "",
        nom,
        flags=re.IGNORECASE,
    )

    cle = normaliser(nom)

    if cle in NOMS_COURTS:
        return NOMS_COURTS[cle]

    # Ne pas inventer de nom lorsque la correspondance est inconnue.
    return nom


def couleur_sport(code_federation: str) -> str:
    """Attribue une couleur stable à un code de fédération."""
    code = str(code_federation)
    if code in ("Football", "111"):
        # Le football, présent partout, prend une couleur de la palette.
        return CATEGORIE_1
    empreinte = hashlib.sha256(code.encode("utf-8")).digest()

    teinte = int.from_bytes(empreinte[:4], "big") / (2**32)
    rouge, vert, bleu = colorsys.hls_to_rgb(teinte, 0.56, 0.62)

    return f"#{round(rouge * 255):02x}{round(vert * 255):02x}{round(bleu * 255):02x}"
