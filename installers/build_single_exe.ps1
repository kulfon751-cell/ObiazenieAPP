<#
Build single-file portable executable using PyInstaller.

Usage (PowerShell, from repository root):
  Set-Location .\Projekt Obciążenie nowa wersja
  .\.venv\Scripts\Activate.ps1
  .\installers\build_single_exe.ps1 -OutputDir C:\Users\<you>\Apps\ObciazenieApp

This script will:
 - create a virtualenv if missing (optional),
 - install PyInstaller in the active venv,
 - run PyInstaller against launcher.py to produce a --onefile exe,
 - copy installers/README_PORTABLE.md next to the exe.
#>
param(
  [string]$OutputDir = "dist",
  [switch]$Clean,
  [string[]]$Include = @('installers','Raport_dane.xlsx','DostepnoscWTygodniach.xlsx','Scalanie17.xlsx','uploaded')
)

Set-StrictMode -Version Latest

if ($Clean -and (Test-Path -Path .\dist)) { Remove-Item -Recurse -Force .\dist }

Write-Output "Locating Python executable..."
$pythonExe = ''
if (Test-Path -Path ".\\.venv\\Scripts\\python.exe") { $pythonExe = Join-Path (Get-Location) ".\\.venv\\Scripts\\python.exe" }
elseif (Test-Path -Path ".\\venv\\Scripts\\python.exe") { $pythonExe = Join-Path (Get-Location) ".\\venv\\Scripts\\python.exe" }
else { $pythonExe = 'python' }
Write-Output "Using python: $pythonExe"

Write-Output "Ensuring PyInstaller is installed (via python -m pip)..."
& $pythonExe -m pip install --upgrade pip pyinstaller | Out-Default

# Build --add-data arguments for each include entry. PyInstaller on Windows uses 'src;dest' (dest is relative inside bundle).
$addDataArgs = @()
foreach ($item in $Include) {
  if (Test-Path -Path $item) {
    $src = $item
    # if it's a directory, preserve directory name as destination; if file, place in '.'
    if ((Get-Item $item).PSIsContainer) {
      $dest = $item.TrimStart('.\\').TrimStart('\\')
    } else {
      $dest = '.'
    }
    $pair = "$src;$dest"
    $addDataArgs += '--add-data'
    $addDataArgs += $pair
  } else {
    Write-Output "Warning: include path not found: $item (skipping)"
  }
}

Write-Output "Building onefile executable with includes: $Include"

$pyinstallerArgs = @('--clean','--noconfirm','--onefile','--name','ObciazenieApp') + $addDataArgs + @('launcher.py')
Write-Output "pyinstaller arguments: $pyinstallerArgs"

Write-Output "Running PyInstaller (via python -m PyInstaller)..."
& $pythonExe -m PyInstaller @pyinstallerArgs | Out-Default

if (-not (Test-Path -Path .\dist\ObciazenieApp.exe)) {
  Write-Error "Build failed: .\dist\ObciazenieApp.exe not found"
  exit 1
}

if (-not (Test-Path -Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }
Copy-Item -Path .\dist\ObciazenieApp.exe -Destination (Join-Path $OutputDir 'ObciazenieApp.exe') -Force
if (Test-Path -Path .\installers\README_PORTABLE.md) { Copy-Item -Path .\installers\README_PORTABLE.md -Destination (Join-Path $OutputDir 'README_PORTABLE.md') -Force }

Write-Output "Built single exe placed in: $OutputDir\ObciazenieApp.exe"

# w katalogu projektu, w PowerShell
. .\.venv\Scripts\Activate.ps1
python .\scripts\merge_scalanie17.py
$env:DATA_FILE_PATH='\\nas1\PRODUKCJA\DostepnoscWTygodniach.xlsx'
$env:PROD_FILE_PATH='\\nas1\PRODUKCJA\Raport_dane.xlsx'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
