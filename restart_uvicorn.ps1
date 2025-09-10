$procs = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -like '*run_uvicorn.py*' -or $_.CommandLine -like '*uvicorn app.main:app*') }
if($procs){
    foreach($p in $procs){ Write-Output "Killing PID $($p.ProcessId)"; Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
}
$p = Start-Process -FilePath 'python' -ArgumentList '"C:\Users\jmichalak\Desktop\Projekt Obciążenie nowa wersja\run_uvicorn.py"' -WindowStyle Hidden -PassThru
Write-Output "Started PID:$($p.Id)"
Start-Sleep -Seconds 1
Try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/' -Method GET -TimeoutSec 5 | Out-Null; Write-Output 'UP' } Catch { Write-Output ('DOWN: '+$_.Exception.Message) }
