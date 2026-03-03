@echo off
setlocal enabledelayedexpansion

echo === Northwind Traders -- Installer ===

REM Python presence
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.9+ from https://www.python.org
    pause
    exit /b 1
)

REM Python version >= 3.9
python -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.9 or later is required.
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo Found: %%v
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo %%v OK

REM Install packages
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo Installation complete. Run app.bat to start the application.
pause
