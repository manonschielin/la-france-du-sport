"""Point d'entrée du dashboard La France du sport."""

from dash import Dash

import config
from src.pages.accueil import creer_page, enregistrer_callbacks
from src.utils.clean_data import clean_data
from src.utils.get_data import get_data


def main() -> None:
    """Prépare les données si besoin, puis lance le dashboard."""
    if not config.DB_PATH.exists():
        get_data()
        clean_data()

    app = Dash(__name__)
    app.layout = creer_page()
    enregistrer_callbacks(app)
    app.run(debug=True)


if __name__ == "__main__":
    main()