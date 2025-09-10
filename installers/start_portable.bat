@echo off
REM Portable launcher for ObciazenieApp (per-user, no admin required)
REM Usage: unzip dist\ObciazenieApp into a folder and place this .bat next to ObciazenieApp.exe

:: Configure UNC paths here if needed (edit before running)
set "PROD_FILE_PATH=\\nas1\Planowanie\Raport_dane.xlsx"
set "DATA_FILE_PATH=\\nas1\Planowanie\DostepnoscWTygodniach.xlsx"

:: Start the application (runs in same folder as this batch)
cd /d "%~dp0"
start "ObciazenieApp" "%~dp0ObciazenieApp.exe"

:: give app a moment to start then open browser
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/"

:: Note: this sets env vars only for this process/session. For persistent per-user vars, use setx or the provided install_per_user.ps1 script.
exit /b 0
