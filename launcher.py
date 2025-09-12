"""Launcher FastAPI dla wersji exe.
Używa zmiennych środowiskowych (PROD_FILE_PATH / DATA_FILE_PATH) lub domyślnych UNC.
Port domyślnie 8000 (PORT env override).
"""
from __future__ import annotations
import os
import pathlib
import sys
import uvicorn
import logging


ROOT = pathlib.Path(__file__).resolve().parent

# Reasonable defaults (can be overridden by env vars)
os.environ.setdefault("PROD_FILE_PATH", str(ROOT / "Raport_dane.xlsx"))
os.environ.setdefault("DATA_FILE_PATH", str(ROOT / "DostepnoscWTygodniach.xlsx"))
os.environ.setdefault("SCALANIE_FILE_PATH", str(ROOT / "Scalanie17.xlsx"))


def ensure_scalanie_csv():
    # Wygeneruj plik scalanie_group_name.csv jeśli brak
    target = ROOT / "scalanie_group_name.csv"
    if target.exists():
        return
    try:
        from scripts import merge_scalanie17

        merge_scalanie17.main()
    except Exception:
        logging.getLogger(__name__).exception("Nie udało się wygenerować scalanie_group_name.csv")


def main():
    # initialize logging for the exe
    try:
        from app.logging_config import setup_logging

        setup_logging(log_file=ROOT / "logs" / "app.log")
    except Exception:
        pass

    ensure_scalanie_csv()

    try:
        from app.main import app
    except Exception:
        # if import fails, try to add ROOT to sys.path and retry
        sys.path.insert(0, str(ROOT))
        from app.main import app

    prod = os.environ.get("PROD_FILE_PATH") or r"\\nas1\PRODUKCJA\Raport_dane.xlsx"
    data = os.environ.get("DATA_FILE_PATH") or r"\\nas1\PRODUKCJA\DostepnoscWTygodniach.xlsx"
    os.environ["PROD_FILE_PATH"] = prod
    os.environ["DATA_FILE_PATH"] = data

    port = int(os.environ.get("PORT", "8000"))
    logger = logging.getLogger(__name__)
    logger.info("[launcher] PROD_FILE_PATH=%s", prod)
    logger.info("[launcher] DATA_FILE_PATH=%s", data)
    logger.info("[launcher] Start na porcie %s", port)

    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
