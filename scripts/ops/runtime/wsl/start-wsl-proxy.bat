@echo off
REM Start WSL proxy in background (enables WSL2 to reach internet via Windows VPN).
REM Run once before using Codex in WSL2.

if "%~1"=="" goto usage
if "%~2"=="" goto usage

echo Starting WSL proxy on %~1:3128 for client CIDR %~2...
start "" /B pythonw "%~dp0wsl_proxy.py" --bind-host "%~1" --allow-cidr "%~2"
echo Proxy started. WSL2 can now use http_proxy=http://%~1:3128
exit /B 0

:usage
echo Usage: %~nx0 WINDOWS_WSL_HOST_IP WSL_CLIENT_CIDR
echo Example: %~nx0 172.30.32.1 172.30.32.0/20
echo The Windows Firewall rule must also restrict TCP 3128 to the same WSL subnet.
exit /B 2
