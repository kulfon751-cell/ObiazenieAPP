@echo off
rem Start script for portable distribution (dist\ObciazenieApp)
set DIST_DIR=%~dp0dist\ObciazenieApp
if exist "%DIST_DIR%\ObciazenieApp.exe" (
  cd /d "%DIST_DIR%"
  start "" "ObciazenieApp.exe"
  timeout /t 2 >nul
  start "" "http://127.0.0.1:8000/"
) else (
  echo Error: "%DIST_DIR%\ObciazenieApp.exe" not found.
  echo Make sure you built the app with PyInstaller and placed the distribution here.
  pause
)
