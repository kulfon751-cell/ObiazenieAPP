<#
Uninstall helper: stops and removes the Windows service and optionally removes machine env vars.
Usage (as Administrator):
    .\uninstall_service.ps1 -InstallDir "C:\Program Files\ObciazenieApp"
#>

param(
    [string]$InstallDir = "C:\Program Files\ObciazenieApp",
    [string]$ServiceName = "ObciazenieApp",
    [switch]$RemoveEnvVars
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

# Stop and delete service
try {
    sc.exe stop "$ServiceName" | Out-Null
    Start-Sleep -Seconds 1
    sc.exe delete "$ServiceName" | Out-Null
    Write-Output "Service $ServiceName removed (if it existed)."
} catch {
    Write-Warning "Failed to remove service $ServiceName: $_"
}

if ($RemoveEnvVars) {
    try {
        [Environment]::SetEnvironmentVariable('PROD_FILE_PATH', $null, 'Machine')
        [Environment]::SetEnvironmentVariable('DATA_FILE_PATH', $null, 'Machine')
        Write-Output "Removed PROD_FILE_PATH and DATA_FILE_PATH from machine environment variables."
    } catch {
        Write-Warning "Failed to remove environment variables: $_"
    }
}

Write-Output "Uninstall complete. You may now delete the installation folder: $InstallDir"
