@echo off
setlocal
chcp 65001 >nul 2>&1
title T-Share v2 - Ethernet Transfer and Deep Verification Suite (Windows)
cd /d "%~dp0"

echo =====================================================================
echo  T-Share v2 - Ethernet Transfer and Deep Verification Cockpit
echo  Platform: Windows (Robocopy / Win32 I/O / SMB Native)
echo =====================================================================

rem 1. Locate Python
set "PYTHON_EXE="
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=py"
    ) else (
        for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
            if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found on your system.
    echo Please download and install Python 3.10+ from https://www.python.org/
    echo Make sure to check 'Add Python to PATH' during installation.
    echo.
    pause
    exit /b 1
)

rem 2. Check and Install Dependencies
echo [*] Checking runtime dependencies...
%PYTHON_EXE% -c "import webview" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Missing dependency: pywebview
    echo [*] Installing required packages from requirements.txt...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install required packages via pip.
        echo Please ensure you have internet access and run:
        echo %PYTHON_EXE% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo [*] Dependencies successfully installed.
) else (
    echo [OK] Runtime dependencies verified.
)

rem 3. Launch T-Share v2 Cockpit
echo [*] Launching T-Share v2 Cockpit...
echo.
%PYTHON_EXE% app.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Application exited with error code %ERRORLEVEL%.
    pause
)
