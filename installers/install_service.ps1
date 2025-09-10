<#
PowerShell helper to register the packaged EXE as a Windows service.
Usage (as Administrator):
    .\install_service.ps1 -InstallDir "C:\Program Files\ObciazenieApp"
If you run the Inno Setup installer that includes this script, it will execute automatically.

The script will:
- Ensure it's running elevated
- Optionally set machine-level environment variables for PROD_FILE_PATH and DATA_FILE_PATH
- Create a service named "ObciazenieApp" pointing to ObciazenieApp.exe (set to automatic start)
- Start the service
#>

param(
    [string]$InstallDir = "C:\Program Files\ObciazenieApp",
    [string]$ServiceName = "ObciazenieApp",
    [string]$DisplayName = "Obciążenie - aplikacja",
    [string]$ProdFilePath = "",
    [string]$DataFilePath = ""
)

function Ensure-RunningAsAdmin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object System.Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "This script must be run as Administrator."
        exit 1
    }
}

Ensure-RunningAsAdmin

# Validate exe
$exe = Join-Path $InstallDir 'ObciazenieApp.exe'
if (-not (Test-Path $exe)) {
    Write-Error "Could not find $exe. Ensure you provided correct InstallDir or installed the package first."
    exit 1
}

# Optionally set machine-level environment variables so the service sees UNC paths
if ($ProdFilePath) {
    [Environment]::SetEnvironmentVariable('PROD_FILE_PATH', $ProdFilePath, 'Machine')
    Write-Output "Set PROD_FILE_PATH = $ProdFilePath"
}
if ($DataFilePath) {
    [Environment]::SetEnvironmentVariable('DATA_FILE_PATH', $DataFilePath, 'Machine')
    Write-Output "Set DATA_FILE_PATH = $DataFilePath"
}

# Create the service using sc.exe
$binPath = "\"$exe\""
Write-Output "Creating service '$ServiceName' -> $binPath"
# If service exists, try to remove first
$existing = sc.exe query "$ServiceName" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Output "Service $ServiceName already exists. Attempting to stop and delete."
    sc.exe stop "$ServiceName" | Out-Null
    Start-Sleep -Seconds 1
    sc.exe delete "$ServiceName" | Out-Null
    Start-Sleep -Seconds 1
}

$createCmd = "sc.exe create `"$ServiceName`" binPath= $binPath start= auto DisplayName= `"$DisplayName`""
Write-Output $createCmd
Invoke-Expression $createCmd

# Set a simple description
try { sc.exe description "$ServiceName" "Usługa uruchamia aplikację Obciążenie" | Out-Null } catch {}

# Start the service
Start-Sleep -Seconds 1
try { Start-Service -Name $ServiceName -ErrorAction Stop; Write-Output "Service $ServiceName started." } catch { Write-Warning "Could not start service automatically. You may start it manually: Start-Service -Name $ServiceName" }

Write-Output "Installation complete. Ensure the service account has access to UNC paths if using network shares." 
