import config
from src.utils.get_data import get_data
from src.utils.clean_data import clean_data


def main():
    if not config.DB_PATH.exists():
        get_data()
        clean_data()


if __name__ == "__main__":
    main()
