@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [AutoShorts] First run: creating environment and installing packages...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 (
    echo Python is not installed. Install Python 3.10+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    pause & exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m streamlit run webui.py --server.port 8501 --browser.gatherUsageStats false
pause
