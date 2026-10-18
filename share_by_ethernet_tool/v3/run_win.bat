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
    echo [ERROR] Python 3 was not found in your PATH.
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

:: Virtual environment setup (optional/recommended)
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
)

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [*] Checking dependencies...
python -c "import webview, psutil" 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required packages (pywebview, psutil)...
    python -m pip install -r requirements.txt
)

echo [*] Starting T-Share v3...
python app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] T-Share exited with an error.
    pause
)
