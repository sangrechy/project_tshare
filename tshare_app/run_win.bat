@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   T-Share: Unified Wire P2P ^& LAN Web Sharing Suite
echo ========================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3 was not found in PATH.
    echo Please install Python 3 from https://python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

if not exist venv (
    echo [*] Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

python -c "import psutil" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required dependencies...
    pip install -r requirements.txt
)

echo [*] Starting T-Share Unified...
python app.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Application exited with code %ERRORLEVEL%.
    pause
)
