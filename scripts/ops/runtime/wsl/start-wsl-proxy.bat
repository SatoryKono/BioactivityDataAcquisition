@echo off
REM Start WSL proxy in background (enables WSL2 to reach internet via Windows VPN).
REM Run once before using Codex in WSL2.

for /f %%I in ('wsl.exe sh -lc "ip route show default ^| awk '{print $3}'"') do set "WSL_HOST_IP=%%I"
if not defined WSL_HOST_IP (
  echo Unable to determine the Windows host address for WSL2.
  exit /b 1
)

echo Starting WSL proxy on %WSL_HOST_IP%:3128...
start "" /B pythonw "%~dp0wsl_proxy.py" --listen-host "%WSL_HOST_IP%" %*
echo Proxy started on the WSL2 virtual interface only.
