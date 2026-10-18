@echo off
echo ============================================================
echo   Setting Ethernet 2 to 192.168.123.1 for Direct Transfer
echo ============================================================
echo.

:: Try netsh first
netsh interface ipv4 add address "Ethernet 2" 192.168.123.1 255.255.255.0 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell -NoProfile -Command "New-NetIPAddress -InterfaceAlias 'Ethernet 2' -IPAddress 192.168.123.1 -PrefixLength 24 -ErrorAction SilentlyContinue"
)

echo Direct wire IP 192.168.123.1 is now configured on Ethernet 2.
echo Windows can now communicate directly with Fedora (192.168.123.2).
echo.
pause
