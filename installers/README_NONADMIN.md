Uruchamianie bez uprawnień Administratora (per-user)

Cel: umożliwić wdrożenie aplikacji na służbowych komputerach bez konieczności wykonywania każdorazowo logowania administratora.

Opcje dostępne:
1) Per-user portable install (bez admin) — polecane dla prostego środowiska
   - Przekaż użytkownikowi plik `installers\ObciazenieApp_installer_bundle.zip`.
   - Poproś użytkownika, aby uruchomił `installers\install_per_user.ps1` (PowerShell) z poziomu swojego konta.
   - Skrypt wypakuje aplikację do `%LOCALAPPDATA%\ObciazenieApp`, utworzy skrót w katalogu Autostart, opcjonalnie utworzy zadanie w Harmonogramie zadań, i ustawi zmienne środowiskowe na poziomie użytkownika (setx).
   - Po instalacji aplikacja uruchamia się w kontekście zalogowanego użytkownika i może używać udziałów sieciowych dostępnych dla tego konta.

2) Centralne wdrożenie (zalecane dla dużej liczby maszyn)
   - Wykorzystaj mechanizmy enterprise: Microsoft Intune, SCCM, GPO (Startup script), lub inny system dystrybucji oprogramowania.
   - Możesz rozpakować zawartość `ObciazenieApp_installer_bundle.zip` na docelowe maszyny i uruchomić `install_per_user.ps1` z uprawnieniami użytkownika lub w ramach logowania.

3) Usługa Windows (wymaga jednorazowo Admina)
   - Rejestracja jako usługa daje pewne zalety (uruchamianie bez potrzeby logowania), ale wymaga uprawnień administratora do zainstalowania usługi. Po zarejestrowaniu warto ustawić konto usługi na konto domenowe z dostępem do udziałów sieciowych.

Uwagi dotyczące udziałów sieciowych (UNC):
- Jeśli aplikacja ma używać zasobów \nas1\Planowanie\..., uruchomienie pod kontem zalogowanego użytkownika jest najprostsze — aplikacja użyje poświadczeń użytkownika (jeśli ma dostęp).
- Jeśli chcesz by aplikacja działała niezależnie od zalogowanego użytkownika, zarejestruj usługę Windows pod kontem domenowym (wymaga admin).

Szybkie komendy dla IT (bez admin):
- Zdalne rozesłanie ZIP i wywołanie skryptu jako użytkownik przy logowaniu (np. poprzez GPO logon script):
    PowerShell -ExecutionPolicy Bypass -File "%APPDATA%\\..\\..\\Local\\Packages\\...\\installers\\install_per_user.ps1"

Jeśli chcesz, przygotuję gotowy pakiet MSI/EXE z instalacją bez interakcji (może wymagać admin do całkowitej automatyzacji) lub pomogę z konfiguracją wdrożenia przez Intune/SCCM.
