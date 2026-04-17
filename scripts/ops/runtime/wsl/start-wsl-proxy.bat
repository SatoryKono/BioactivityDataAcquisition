@echo off
REM Start WSL proxy in background (enables WSL2 to reach internet via Windows VPN).
REM Run once before using Codex in WSL2.

echo Starting WSL proxy on port 3128...
start /B pythonw "%~dp0wsl_proxy.py"
echo Proxy started. WSL2 can now use http_proxy=http://HOST_IP:3128
