@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [AutoShorts] Downloading the latest version from GitHub...
git pull
if not exist ".venv\Scripts\python.exe" ( py -3 -m venv .venv 2>nul || python -m venv .venv )
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
echo Done.
pause
