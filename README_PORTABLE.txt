ObciazenieApp - portable distribution (PyInstaller --onedir)

Overview:
This README explains how to build a portable folder distribution using PyInstaller and how to run the app.
The app is a FastAPI server that serves a single-page UI; it expects Excel files as data: Raport_dane.xlsx and DostepnoscWTygodniach.xlsx.

Build (PowerShell, from project root):
1. Activate virtualenv:
   & ".\.venv\Scripts\Activate.ps1"

2. Install dependencies (if not already):
   pip install pyinstaller pandas openpyxl uvicorn fastapi

3. Build in portable folder mode (recommended):
   pyinstaller --noconfirm --onedir `
     --name ObciazenieApp `
     --add-data "Raport_dane.xlsx;." `
     --add-data "DostepnoscWTygodniach.xlsx;." `
     run_uvicorn.py

Notes:
- The built executable will be in dist\ObciazenieApp\ObciazenieApp.exe
- To test, run the exe from a console to see logs, then open http://127.0.0.1:8000/ in a browser.
- To update data: replace Raport_dane.xlsx or DostepnoscWTygodniach.xlsx in the distribution folder.

Troubleshooting:
- If exe fails on startup with ImportError, run it from the console to see the traceback. Use --hidden-import modulename when rebuilding if necessary.
- If pandas/openpyxl cause issues, add --hidden-import openpyxl to the pyinstaller command.
- If you want a single-file exe, use --onefile but be aware of AV false positives and slower startup (extracts to %TEMP%).

Portable start script:
Use start.bat (provided) placed in the repository root. It expects the dist folder in the repository root.

Optional improvements:
- Add a config.json to point to external data files and modify app/main.py to read it. This allows replacing Excel files without rebuilding.
- Wrap UI in pywebview for a true native-window app (requires WebView2 runtime or CEF and increases distribution size).

If you want, I can:
- Add `config.json` + small code change in `app/main.py` so data paths are configurable (recommended). 
- Prepare a --onefile build or a pywebview-based GUI.

End of README
