<#
Per-user uninstall: removes scheduled task, startup shortcut and installation folder
Usage (run as the same user who installed):
    .\uninstall_per_user.ps1 [-Dest "$env:LOCALAPPDATA\\ObciazenieApp"] [-RemoveEnvVars]
#>
param(
    [string]$Dest = "$env:LOCALAPPDATA\\ObciazenieApp",
    [switch]$RemoveEnvVars
)

function Info($m){ Write-Output "[INFO] $m" }
function Warn($m){ Write-Warning "[WARN] $m" }

try{
    $taskName = 'ObciazenieApp'
    schtasks /Delete /TN $taskName /F 2>$null | Out-Null
    Info "Removed scheduled task (if existed): $taskName"

    $lnkPath = Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup') 'ObciazenieApp.lnk'
    if (Test-Path $lnkPath) { Remove-Item $lnkPath -Force; Info "Removed startup shortcut" }

    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force; Info "Removed installation folder: $Dest" }

    if ($RemoveEnvVars) {
        [Environment]::SetEnvironmentVariable('PROD_FILE_PATH', $null, 'User')
        [Environment]::SetEnvironmentVariable('DATA_FILE_PATH', $null, 'User')
        Info "Removed user env vars PROD_FILE_PATH and DATA_FILE_PATH"
    }
    Info "Uninstall per-user complete."
} catch {
    Warn $_.Exception.Message
    exit 1
}
