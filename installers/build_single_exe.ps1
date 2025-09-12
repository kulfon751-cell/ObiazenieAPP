param(
    [switch]$Clean
)

Set-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent) ; Set-Location ..

Write-Host "Building single-file exe with PyInstaller..."

# find python executable (prefer venv)
$venvPy = Join-Path -Path . -ChildPath ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $python = $venvPy
} else {
    $python = "python"
}

# ensure PyInstaller installed
& $python -m pip install --upgrade pip | Out-Null
& $python -m pip install pyinstaller --quiet | Out-Null

$specName = "ObciazenieApp"
$distDir = Join-Path -Path (Get-Location) -ChildPath "dist"

if ($Clean -and (Test-Path $distDir)) {
    Remove-Item -Recurse -Force $distDir
}

param(
    [switch]$Clean,
    [string]$OutputDir = "installers\portable"
)

Set-StrictMode -Version Latest

# ensure we're at repository root
Set-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent) ; Set-Location ..

Write-Host "Building single-file exe with PyInstaller..."

# locate python (prefer .venv)
$pythonExe = if (Test-Path -Path ".\.venv\Scripts\python.exe") { Join-Path (Get-Location) ".\.venv\Scripts\python.exe" } else { 'python' }
Write-Host "Using python: $pythonExe"

# install pyinstaller if missing
& $pythonExe -m pip install --upgrade pip pyinstaller | Out-Null

$name = 'ObciazenieApp'

if ($Clean -and (Test-Path -Path .\dist)) { Remove-Item -Recurse -Force .\dist }

# build includes if present
$includes = @('Raport_dane.xlsx','DostepnoscWTygodniach.xlsx','Scalanie17.xlsx','installers','uploaded')
$addArgs = @()
foreach ($i in $includes) {
    if (Test-Path $i) { $addArgs += '--add-data'; $addArgs += "$i;." }
}

$pyArgs = @('--clean','--noconfirm','--onefile','--name',$name) + $addArgs + @('launcher.py')

Write-Host "Running PyInstaller..."
& $pythonExe -m PyInstaller @pyArgs 2>&1 | Tee-Object -FilePath installers\pyinstaller_build.log

if (-not (Test-Path -Path .\dist\$name.exe)) {
    Write-Error "Build failed: .\dist\$name.exe not found. See installers\pyinstaller_build.log"
    exit 1
}

if (-not (Test-Path -Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }
Copy-Item -Path .\dist\$name.exe -Destination (Join-Path $OutputDir "$name.exe") -Force
Write-Host "Built single exe placed in: $OutputDir\$name.exe"

