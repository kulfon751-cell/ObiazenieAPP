param(
    [string]$TargetPath = ".\installers\start_portable.bat",
    [string]$ShortcutName = "ObciazenieApp.lnk",
    [switch]$UsePortableExe
)

Set-StrictMode -Version Latest

function Resolve-Target {
    param($p)
    $full = Resolve-Path -Path $p -ErrorAction SilentlyContinue
    if ($full) { return $full.ProviderPath }
    return $null
}

# prefer start_portable.bat which sets env vars for session; fallback to portable exe if requested or .bat missing
$defaultBat = Join-Path (Get-Location) 'installers\start_portable.bat'
$portableExe = Join-Path (Get-Location) 'installers\portable\ObciazenieApp.exe'

if ($UsePortableExe -or -not (Test-Path -Path $defaultBat)) {
    if (Test-Path -Path $portableExe) { $TargetPath = $portableExe } else { $TargetPath = $defaultBat }
}

$targetFull = Resolve-Target $TargetPath
if (-not $targetFull) {
    Write-Error "Target not found: $TargetPath"
    exit 1
}

$startup = [Environment]::GetFolderPath('Startup')
$linkPath = Join-Path $startup $ShortcutName

Write-Output "Creating shortcut: $linkPath -> $targetFull"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($linkPath)
$sc.TargetPath = $targetFull
$sc.WorkingDirectory = Split-Path $targetFull -Parent
if ($targetFull -like '*.bat') { $sc.Arguments = '' }
$sc.IconLocation = $targetFull
$sc.Save()

Write-Output "Shortcut created in user Startup folder: $linkPath"

# w katalogu projektu, w PowerShell
. .\.venv\Scripts\Activate.ps1
python .\scripts\merge_scalanie17.py
$env:DATA_FILE_PATH='\\nas1\PRODUKCJA\DostepnoscWTygodniach.xlsx'
$env:PROD_FILE_PATH='\\nas1\PRODUKCJA\Raport_dane.xlsx'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
git add scripts\merge_scalanie17.py
git commit -m "scripts: zapis pustego scalanie_group_name.csv gdy brak/err pliku Scalanie17.xlsx"
git push origin HEAD
