@echo off
title T-Share v2 - Ethernet Transfer & Deep Verification Suite
cd /d "%~dp0"
python app.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with code %ERRORLEVEL%.
    pause
)
