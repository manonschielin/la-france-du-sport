"""Point d'entrée du dashboard La France du sport."""

from dash import Dash, Input, Output, dcc, html

import config
from src.components.footer import creer_footer
from src.components.header import creer_header
from src.components.navbar import creer_navbar
from src.pages import accueil, carte, tendances
from src.utils.clean_data import clean_data
from src.utils.get_data import get_data

# Adresse de chaque page -> module qui la construit (creer_page et enregistrer_callbacks).
PAGES = {
    "/": accueil,
    "/carte": carte,
    "/tendances": tendances,
}


def creer_application() -> Dash:
    """Crée l'application : en-tête, navigation, page affichée selon l'adresse, pied de page."""
    # Les composants d'une page n'existent que lorsqu'elle est affichée :
    # sans cette option, Dash signale des callbacks vers des composants absents.
    app = Dash(__name__, suppress_callback_exceptions=True, title="La France du sport")

    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            creer_header(),
            creer_navbar(),
            html.Main(
                id="contenu-page",
                style={"maxWidth": "1600px", "margin": "auto", "padding": "20px 30px"},
            ),
            creer_footer(),
        ],
        # Fond blanc explicite : sinon le texte devient illisible dans un navigateur en mode sombre.
        style={
            "fontFamily": "Arial, sans-serif",
            "backgroundColor": "white",
            "color": "#111827",
            "minHeight": "100vh",
        },
    )

    @app.callback(Output("contenu-page", "children"), Input("url", "pathname"))
    def afficher_page(adresse: str | None) -> html.Div:
        """Affiche la page qui correspond à l'adresse (l'accueil si elle est inconnue)."""
        page = PAGES.get(adresse or "/", accueil)
        return page.creer_page()

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