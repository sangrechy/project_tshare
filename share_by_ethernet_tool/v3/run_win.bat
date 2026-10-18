@echo off
setlocal enabledelayedexpansion
title T-Share v3 - Direct Wire Ethernet Transfer

cd /d "%~dp0"

echo ========================================================
echo   T-Share v3: High-Speed Direct Ethernet File Transfer
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

:: Optional virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [*] Checking dependencies...
python -c "import webview, psutil" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required packages...
    python -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [WARNING] Pip install failed or required packages missing. Trying direct install...
        python -m pip install pywebview psutil
    )
)

echo [*] Starting T-Share v3...
python app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] T-Share v3 exited with code %errorlevel%.
    pause
)
