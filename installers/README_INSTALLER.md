Instrukcja instalacji i uruchomienia na innych komputerach

Opcje dostępne w katalogu `installers/`:

1) Instalator Inno Setup (`installers/inno/ObciazenieApp.iss`)
   - Kompilacja: zainstaluj Inno Setup (https://jrsoftware.org/isinfo.php) i skompiluj skrypt `.iss` (ISCC.exe)
   - Skrypt zakłada, że folder dystrybucyjny PyInstaller `dist\ObciazenieApp` jest dostępny w katalogu źródłowym podczas kompilacji.
   - Instalator skopiuje pliki do `C:\Program Files\ObciazenieApp` (domyślnie) i wywoła skrypt `install_service.ps1` (wymaga uprawnień Administratora).

2) Skrypty PowerShell do instalacji/usunięcia usługi
   - `install_service.ps1` - rejestruje `ObciazenieApp.exe` jako usługę Windows (nazwa domyślna: `ObciazenieApp`) i może ustawić zmienne środowiskowe machine-level `PROD_FILE_PATH` i `DATA_FILE_PATH` (jeśli przekażesz parametry)
   - `uninstall_service.ps1` - zatrzymuje i usuwa usługę oraz opcjonalnie usuwa zmienne środowiskowe

Przykładowe użycie (jako Administrator):

# Ustawienie ścieżek UNC (przykład tymczasowy dla sesji PowerShell)
$env:PROD_FILE_PATH='\\\\nas1\\Planowanie\\Raport_dane.xlsx'
$env:DATA_FILE_PATH='\\\\nas1\\Planowanie\\DostepnoscWTygodniach.xlsx'

# Uruchomienie instalatora (po skompilowaniu Inno) lub bez instalatora:
# Po wypakowaniu/zainstalowaniu do C:\Program Files\ObciazenieApp
.
# Przy użyciu gotowego EXE: (uruchom PowerShell jako administrator)
.
# Uruchom instalator usługi z folderu instalacyjnego
PowerShell -ExecutionPolicy Bypass -NoProfile -File "C:\Program Files\ObciazenieApp\install_service.ps1" -InstallDir "C:\Program Files\ObciazenieApp" -ProdFilePath "\\\\nas1\\Planowanie\\Raport_dane.xlsx" -DataFilePath "\\\\nas1\\Planowanie\\DostepnoscWTygodniach.xlsx"

Uwaga dotycząca udziałów sieciowych (UNC):
- Jeśli serwis będzie uruchamiany pod kontem systemowym (LocalSystem), dostęp do udziałów sieciowych może być ograniczony. Najpewniejsze jest uruchomienie usługi pod kontem domenowym z dostępem do udziału lub przypisanie stałych poświadczeń.
- Alternatywnie można uruchamiać EXE jako zadanie zaplanowane lub ręczny skrót uruchamiany przez zalogowanego użytkownika, który ma uprawnienia do udziału.

Jeśli chcesz, mogę:
- skompilować Inno Setup installer lokalnie i załączyć gotowy instalator do repo (jeśli masz zgodę na dodanie binariów),
- albo pozostawić tylko skrypty i instrukcję i pomóc zdalnie zainstalować usługę na konkretnych maszynach.
