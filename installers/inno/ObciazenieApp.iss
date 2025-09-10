; Inno Setup script to package the PyInstaller --onedir distribution located in `dist\ObciazenieApp`
[Setup]
AppName=ObciazenieApp
AppVersion=1.0
DefaultDirName={pf}\ObciazenieApp
DefaultGroupName=ObciazenieApp
OutputBaseFilename=ObciazenieAppInstaller
Compression=lzma
SolidCompression=yes

[Files]
; Copy the entire dist\ObciazenieApp folder into the installation directory
Source: "{#SourcePath}\dist\ObciazenieApp\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Also include the install/uninstall helper scripts if present in installers folder
Source: "installers\\install_service.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "installers\\uninstall_service.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ObciazenieApp"; Filename: "{app}\ObciazenieApp.exe"
Name: "{group}\Otwórz w przeglądarce"; Filename: "{app}\start_with_browser.bat"

[Run]
; Optionally run the service installation script immediately after install (requires admin)
Filename: "powershell"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File \"{app}\\install_service.ps1\""; Flags: runhidden

[UninstallRun]
Filename: "powershell"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File \"{app}\\uninstall_service.ps1\""; Flags: runhidden

; Note: When running Inno Setup compile, define SourcePath preprocessor variable if building from a different folder, e.g.:
; ISCC.exe /DSourcePath="C:\path\to\project" ObciazenieApp.iss
