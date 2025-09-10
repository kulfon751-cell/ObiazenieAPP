Portable usage (single-user, no admin)

1. Rozpakuj `installers\ObciazenieApp_installer_bundle.zip` na dysk użytkownika, np. `C:\Users\<user>\Apps\ObciazenieApp`.
2. W folderze powinny być: `ObciazenieApp.exe`, `_internal\`, `start_portable.bat` oraz inne pliki.
3. (Opcjonalnie) edytuj `start_portable.bat` i ustaw ścieżki UNC dla `PROD_FILE_PATH` i `DATA_FILE_PATH` jeśli chcesz, żeby sesja uruchomieniowa korzystała z nich.
4. Uruchom `start_portable.bat` — skrypt ustawi zmienne środowiskowe dla procesu i uruchomi aplikację, a potem otworzy przeglądarkę na http://127.0.0.1:8000/.

Caveats and notes:
- `start_portable.bat` sets env vars only for its session. If chcesz, żeby były trwałe, użyj `setx` lub `install_per_user.ps1`.
- Jeżeli potrzebujesz, mogę przygotować wersję single-exe (PyInstaller onefile) lub skrypt, który utworzy skrót na pulpicie/Autostart.
- Testowane na Windows 10/11. Upewnij się, że użytkownik ma dostęp do udziałów sieciowych (UNC).
