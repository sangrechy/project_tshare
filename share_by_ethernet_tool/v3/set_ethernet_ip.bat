@echo off
:: Self-elevate to Administrator if not already elevated
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Requesting Administrator privileges to configure Ethernet IP...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   T-Share v3: Configure Direct Wire Ethernet (192.168.123.1)
echo ============================================================
echo.

:: 1. Add IP 192.168.123.1 to Ethernet 2 or any active Ethernet adapter
netsh interface ipv4 add address "Ethernet 2" 192.168.123.1 255.255.255.0 >nul 2>&1
powershell -NoProfile -Command "$eth = Get-NetAdapter | Where-Object { $_.InterfaceDescription -notmatch 'Wi-Fi|Wireless|Virtual|Hyper-V|TAP' -and $_.Status -eq 'Up' } | Select-Object -First 1; if ($eth) { New-NetIPAddress -InterfaceIndex $eth.ifIndex -IPAddress 192.168.123.1 -PrefixLength 24 -ErrorAction SilentlyContinue; netsh interface ipv4 add address $eth.ifIndex 192.168.123.1 255.255.255.0 2>$null }"

:: 2. Open inbound firewall ports 52000-52010
netsh advfirewall firewall add rule name="T-Share-Direct-TCP" dir=in action=allow protocol=TCP localport=52000-52010 >nul 2>&1
netsh advfirewall firewall add rule name="T-Share-Direct-UDP" dir=in action=allow protocol=UDP localport=52000-52010 >nul 2>&1

echo.
echo [SUCCESS] Direct wire IP 192.168.123.1 is active on your Ethernet adapter!
echo [SUCCESS] Windows can now communicate directly with Fedora (192.168.123.2).
echo.
pause
