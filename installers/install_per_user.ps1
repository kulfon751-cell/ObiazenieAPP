<#
Instalacja "per-user" (bez uprawnień Administratora).
Uwaga: uruchom na koncie użytkownika końcowego. Skrypt rozpakowuje przygotowany zip z folderem dystrybucyjnym i tworzy skrót w katalogu Autostart oraz zadanie w Harmonogramie zadań logujące się przy starcie użytkownika.

Usage (run as the target user):
    .\install_per_user.ps1 [-ZipPath ".\\installers\\ObciazenieApp_installer_bundle.zip"] [-Dest "$env:LOCALAPPDATA\\ObciazenieApp"] [-ProdFilePath "\\\\nas1\\Planowanie\\Raport_dane.xlsx"] [-DataFilePath "\\\\nas1\\Planowanie\\DostepnoscWTygodniach.xlsx"]

#>
param(
    [string]$ZipPath = "$PSScriptRoot\ObciazenieApp_installer_bundle.zip",
    [string]$Dest = "$env:LOCALAPPDATA\ObciazenieApp",
    [string]$ProdFilePath = "\\nas1\PRODUKCJA\Raport_dane.xlsx",
    [string]$DataFilePath = "\\nas1\PRODUKCJA\DostepnoscWTygodniach.xlsx",
    [switch]$CreateScheduledTask = $true
)

function Info($msg){ Write-Output "[INFO] $msg" }
function Err($msg){ Write-Error "[ERROR] $msg" }

try{
    Info "Destination: $Dest"

    if (Test-Path $ZipPath) {
        Info "Zip found: $ZipPath -> extracting to $Dest"
        if (-not (Test-Path $Dest)) { New-Item -ItemType Directory -Path $Dest | Out-Null }
        Expand-Archive -LiteralPath $ZipPath -DestinationPath $Dest -Force
    } elseif (Test-Path "..\dist\ObciazenieApp") {
        Info "Found dist folder; copying to $Dest"
        if (-not (Test-Path $Dest)) { New-Item -ItemType Directory -Path $Dest | Out-Null }
        robocopy "..\dist\ObciazenieApp" $Dest /MIR | Out-Null
    } else {
        Err "Neither zip ($ZipPath) nor ../dist/ObciazenieApp found. Place distribution bundle in installers/ or run from project root where dist exists."
        exit 1
    }

    $exe = Join-Path $Dest 'ObciazenieApp.exe'
    if (-not (Test-Path $exe)) { Err "Executable not found at $exe"; exit 1 }

    # create Startup shortcut
    $startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
    if (-not (Test-Path $startupDir)) { New-Item -ItemType Directory -Path $startupDir | Out-Null }
    $lnkPath = Join-Path $startupDir 'ObciazenieApp.lnk'
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($lnkPath)
    $sc.TargetPath = $exe
    $sc.Arguments = ''
    $sc.WorkingDirectory = $Dest
    $sc.IconLocation = "$exe,0"
    $sc.Save()
    Info "Created startup shortcut: $lnkPath"

    # create scheduled task for current user (runs at logon)
    if ($CreateScheduledTask) {
        $taskName = 'ObciazenieApp'
        # remove existing task for current user if exists
        schtasks /Query /TN $taskName 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            schtasks /Delete /TN $taskName /F | Out-Null
        }
        $tr = "`"$exe`""
        schtasks /Create /SC ONLOGON /RL LIMITED /TN $taskName /TR $tr /F | Out-Null
        if ($LASTEXITCODE -eq 0) { Info "Scheduled task created: $taskName (runs at user logon)" } else { Err "Failed to create scheduled task (this may be okay on some systems)." }
    }

    # set user environment variables (so the app picks UNC paths without admin)
    if ($ProdFilePath) { setx PROD_FILE_PATH "$ProdFilePath" | Out-Null; Info "Set user PROD_FILE_PATH = $ProdFilePath" }
    if ($DataFilePath) { setx DATA_FILE_PATH "$DataFilePath" | Out-Null; Info "Set user DATA_FILE_PATH = $DataFilePath" }

    # start the app now
    Start-Process -FilePath $exe -WorkingDirectory $Dest
    Info "Started application."
    Info "Installation per-user complete. The app will start automatically at next logon."
} catch {
    Err $_.Exception.Message
    exit 1
}
