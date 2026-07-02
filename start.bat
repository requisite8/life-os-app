@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "c:\Users\ACER\OneDrive\Desktop\ml\requisite_focus"

if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "K=%%A"
    set "V=%%B"
    if not "!K!"=="" if /i not "!K:~0,1!"=="#" set "!K!=!V!"
  )
)

echo ==========================================
echo Life OS backend start
echo URL: http://127.0.0.1:8020
echo ==========================================

if not exist "venv\Scripts\python.exe" (
  echo [ERROR] Python venv not found: venv\Scripts\python.exe
  pause
  exit /b 1
)

"venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8020 --reload
pause
