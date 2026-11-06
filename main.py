"""Point d'entrée du dashboard La France du sport."""

from dash import Dash, Input, Output, dcc, html

import config
from src.components.filtres import (
    FILTRES_PAR_PAGE,
    LARGEURS,
    STYLE_FILTRES,
    TOUS_LES_FILTRES,
    creer_filtres,
)
from src.components.footer import creer_footer
from src.components.header import creer_header
from src.components.navbar import creer_navbar
from src.pages import accueil, carte, fetiches, profils, tendances
from src.utils import couleurs
from src.utils.clean_data import clean_data
from src.utils.get_data import get_data

# Adresse de chaque page -> module qui la construit (creer_page et enregistrer_callbacks).
PAGES = {
    "/": accueil,
    "/carte": carte,
    "/tendances": tendances,
    "/profils": profils,
    "/fetiches": fetiches,
}


def creer_application() -> Dash:
    """Crée l'application : en-tête, navigation, page affichée selon l'adresse, pied de page."""
    # Les composants d'une page n'existent que lorsqu'elle est affichée :
    # sans cette option, Dash signale des callbacks vers des composants absents.
    app = Dash(__name__, suppress_callback_exceptions=True, title="La France du sport")

    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            # En-tête, navigation et filtres restent visibles quand on descend dans la page.
            html.Div(
                [creer_header(), creer_navbar(), creer_filtres()],
                style={"position": "sticky", "top": "0", "zIndex": 1000},
            ),
            html.Main(
                id="contenu-page",
                style={"maxWidth": "1600px", "margin": "auto", "padding": "20px 30px"},
            ),
            creer_footer(),
        ],
        # Fond blanc explicite : sinon le texte devient illisible dans un navigateur en mode sombre.
        style={
            "fontFamily": "Arial, sans-serif",
            "backgroundColor": couleurs.FOND_GENERAL,
            "color": couleurs.BLEU_MARINE,
            "minHeight": "100vh",
        },
    )

    @app.callback(Output("contenu-page", "children"), Input("url", "pathname"))
    def afficher_page(adresse: str | None) -> html.Div:
        """Affiche la page qui correspond à l'adresse (l'accueil si elle est inconnue)."""
        page = PAGES.get(adresse or "/", accueil)
        return page.creer_page()

    @app.callback(
        [Output("zone-filtres", "style")] + [Output(bloc, "style") for bloc in TOUS_LES_FILTRES],
        Input("url", "pathname"),
    )
    def afficher_filtres(adresse: str | None) -> list[dict]:
        """N'affiche que les filtres qui agissent sur la page ouverte (aucun s'il n'y en a pas)."""
        utiles = FILTRES_PAR_PAGE.get(adresse or "/", [])
        zone = STYLE_FILTRES if utiles else {**STYLE_FILTRES, "display": "none"}
        blocs = [LARGEURS[bloc] if bloc in utiles else {"display": "none"} for bloc in TOUS_LES_FILTRES]
        return [zone, *blocs]

    for page in PAGES.values():
        page.enregistrer_callbacks(app)

    return app


def main() -> None:
    """Prépare les données si besoin, puis lance le dashboard."""
    if not config.DB_PATH.exists():
        get_data()
        clean_data()

    creer_application().run(debug=True)


if __name__ == "__main__":
    main()