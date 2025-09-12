"""Launcher used by PyInstaller single-file exe.

Sets environment defaults, ensures scalanie_group_name.csv exists by calling
scripts.merge_scalanie17.main(), then starts the FastAPI app with uvicorn.
"""
from __future__ import annotations
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent

# Reasonable defaults (can be overridden by env vars)
os.environ.setdefault("PROD_FILE_PATH", str(ROOT / "Raport_dane.xlsx"))
os.environ.setdefault("DATA_FILE_PATH", str(ROOT / "DostepnoscWTygodniach.xlsx"))
os.environ.setdefault("SCALANIE_FILE_PATH", str(ROOT / "Scalanie17.xlsx"))


def ensure_scalanie_csv():
    try:
        from scripts import merge_scalanie17
        out = ROOT / "scalanie_group_name.csv"
        # call main to (re)generate CSV if needed
        merge_scalanie17.main(os.environ.get("SCALANIE_FILE_PATH"), str(out))
    except Exception:
        # don't crash the launcher — app can still run without scalanie mapping
        pass


def main():
    ensure_scalanie_csv()
    # import app and run uvicorn
    try:
        from app.main import app
    except Exception:
        # if import fails, try to add ROOT to sys.path and retry
        sys.path.insert(0, str(ROOT))
        from app.main import app

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
"""
Launcher FastAPI dla wersji exe.
Używa zmiennych środowiskowych (PROD_FILE_PATH / DATA_FILE_PATH) lub domyślnych UNC.
Port domyślnie 8000 (PORT env override).
"""
import os
import pathlib
import uvicorn
from app.main import app  # zakładam że app.main zawiera FastAPI() = app

ROOT = pathlib.Path(__file__).resolve().parent


def ensure_scalanie_csv():
    # Wygeneruj plik scalanie_group_name.csv jeśli brak
    target = ROOT / "scalanie_group_name.csv"
    if target.exists():
        return
    try:
        from scripts import merge_scalanie17

        merge_scalanie17.main()
    except Exception as e:
        print(f"[launcher] Nie udało się wygenerować scalanie_group_name.csv: {e}")


def main():
    ensure_scalanie_csv()

    prod = os.environ.get("PROD_FILE_PATH") or r"\\nas1\PRODUKCJA\Raport_dane.xlsx"
    data = os.environ.get("DATA_FILE_PATH") or r"\\nas1\PRODUKCJA\DostepnoscWTygodniach.xlsx"
    os.environ["PROD_FILE_PATH"] = prod
    os.environ["DATA_FILE_PATH"] = data

    port = int(os.environ.get("PORT", "8000"))
    print(f"[launcher] PROD_FILE_PATH={prod}")
    print(f"[launcher] DATA_FILE_PATH={data}")
    print(f"[launcher] Start na porcie {port}")

    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
