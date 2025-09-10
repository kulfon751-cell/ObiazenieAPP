@echo off
chcp 65001 >nul
cd /d "C:\Users\jmichalak\Desktop\Projekt Obciążenie nowa wersja"
"C:\Users\jmichalak\AppData\Local\Microsoft\WindowsApps\python3.11.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
