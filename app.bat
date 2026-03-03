@echo off
setlocal enabledelayedexpansion

REM Python presence
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.9+ from https://www.python.org
    pause
    exit /b 1
)

REM Dependency check
python -c "import textual, plotext, fpdf, PIL, qrcode, fastapi, uvicorn, barcode" >nul 2>&1
if errorlevel 1 (
    echo Some dependencies are missing. Running install.bat ...
    call "%~dp0install.bat"
    if errorlevel 1 exit /b 1
)

python "%~dp0app.py"
