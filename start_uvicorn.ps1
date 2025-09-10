$p = Start-Process -FilePath 'C:\Users\jmichalak\AppData\Local\Microsoft\WindowsApps\python3.11.exe' -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory 'C:\Users\jmichalak\Desktop\Projekt Obciążenie nowa wersja' -WindowStyle Hidden -PassThru
Write-Output "PID:$($p.Id)"
Start-Sleep -Seconds 1
Try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/' -Method GET -TimeoutSec 5 } Catch { Write-Output "ERR:" + $_.Exception.Message }
