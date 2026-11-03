"""Palette de couleurs du dashboard : à utiliser partout au lieu d'écrire les codes en dur."""

# Interface
BLEU_MARINE = "#00327D"        # titres et navigation
BLEU_CLAIR = "#70CBFF"         # accents
GRIS_CLAIR = "#E6E6E4"         # fonds secondaires
FOND_GENERAL = "#F7F8FA"       # fond général du dashboard
BLANC = "#FFFFFF"              # fond des cartes de chiffres clés (KPI) et des graphiques
FOND_CARTES_GEO = "#EEF3F8"    # fond des cartes géographiques
BORDURES = "#E6EAF0"           # bordures et grilles

# Graphiques
UNE_COULEUR = "#5B6EE1"        # graphiques à une seule couleur
CATEGORIE_1 = "#3178C6"        # première catégorie (hommes, football)
CATEGORIE_2 = "#20B5A5"        # deuxième catégorie (femmes)
POSITIF = "#64D870"            # résultat positif (progression)
NEGATIF = "#F05177"            # résultat négatif (recul)
MISE_EN_AVANT = "#C65CDE"      # indicateur à mettre en avant (ex. : l'année choisie)

# Courbes de plusieurs séries (une couleur par sport comparé)
SERIES = [CATEGORIE_1, CATEGORIE_2, MISE_EN_AVANT, UNE_COULEUR, BLEU_CLAIR]

# Échelle des cartes en dégradé, du plus faible au plus fort
ECHELLE_CARTE = ["#DCE8FF", "#B8CEFF", "#8DAEFF", "#5B6EE1", "#2F4FA8"]
# Même échelle au format attendu par Plotly : [[position entre 0 et 1, couleur], ...]
ECHELLE_PLOTLY = [[i / (len(ECHELLE_CARTE) - 1), couleur] for i, couleur in enumerate(ECHELLE_CARTE)]
