"""Page d'accueil : présentation du projet, chiffres clés et accès aux autres pages."""

from dash import Dash, dcc, html

from src.utils import couleurs
from src.utils.indicateurs import chiffres_cles

STYLE_CARTE = {
    "flex": "1 1 0",
    "minWidth": "180px",
    "backgroundColor": couleurs.BLANC,
    "border": f"1px solid {couleurs.BORDURES}",
    "borderRadius": "8px",
    "padding": "16px",
    "textAlign": "center",
}


def creer_chiffre(valeur: str, legende: str) -> html.Div:
    """Une carte avec un chiffre clé et sa légende."""
    return html.Div(
        [
            html.Div(valeur, style={"fontSize": "28px", "fontWeight": "bold", "color": couleurs.BLEU_MARINE}),
            html.Div(legende, style={"fontSize": "14px", "color": couleurs.BLEU_MARINE}),
        ],
        style=STYLE_CARTE,
    )


def creer_page() -> html.Div:
    """Présentation du dashboard, chiffres clés et liens vers les pages."""
    chiffres = chiffres_cles()
    licences = f"{int(chiffres['licences']) / 1_000_000:.1f} M".replace(".", ",")
    part_femmes = f"{chiffres['part_femmes']} %".replace(".", ",")

    return html.Div(
        [
            html.H2("Bienvenue"),
            html.P(
                "Ce dashboard explore les licences sportives délivrées par les fédérations "
                "françaises, commune par commune, de 2012 à 2023 : quels sports sont pratiqués, "
                "où, par qui, et comment la pratique a évolué."
            ),

            # Chiffres clés de la dernière année
            html.H3(f"Les chiffres clés de {chiffres['annee']}"),
            html.Div(
                [
                    creer_chiffre(licences, "licences sportives (fédérations unisport)"),
                    creer_chiffre(part_femmes, "de femmes parmi les licenciés"),
                    creer_chiffre(str(chiffres["sport_numero_un"]), "sport n°1 en France"),
                    creer_chiffre(str(chiffres["nb_sports"]), "sports différents"),
                    creer_chiffre(str(chiffres["annee_record"]), "année record de licences"),
                ],
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "30px"},
            ),

            # Accès aux pages
            html.H3("Que voulez-vous découvrir ?"),
            html.Ul(
                [
                    html.Li([
                        dcc.Link("Explorer la carte", href="/carte"),
                        (" : le sport dominant de chaque région, département et commune, "
                         "l'évolution du nombre de licences, le classement des sports et la "
                         "pyramide des âges des licenciés."),
                    ]),
                    html.Li([
                        dcc.Link("Découvrir les profils", href="/profils"),
                        " : les sports les plus féminins ou masculins et les profils d’âge.",
                    ]),
                    html.Li([
                        dcc.Link("Découvrir les tendances", href="/tendances"),
                        (" : évolutions nationales, baisse et reprise autour du Covid, "
                         "comparaison de plusieurs sports."),
                    ]),
                ],
                style={"lineHeight": "1.8"},
            ),

            html.P(
                "Les chiffres portent sur les fédérations unisport (olympiques et non olympiques) ; "
                "les fédérations multisports et scolaires ne sont pas comptées.",
                style={"fontSize": "13px", "color": couleurs.BLEU_MARINE},
            ),
        ],
    )


def enregistrer_callbacks(app: Dash) -> None:
    """La page d'accueil n'a pas de callback : la fonction existe pour garder le même modèle."""