@echo off
REM Start WSL proxy in background (enables WSL2 to reach internet via Windows VPN).
REM Run once before using Codex in WSL2.

for /f %%I in ('wsl.exe sh -lc "ip route show default ^| awk '{print $3}'"') do set "WSL_HOST_IP=%%I"
if not defined WSL_HOST_IP (
  echo Unable to determine the Windows host address for WSL2.
  exit /b 1
)

echo Starting WSL proxy on %WSL_HOST_IP%:3128 for the detected WSL2 subnet...
start "" /B pythonw "%~dp0wsl_proxy.py" --bind-host "%WSL_HOST_IP%" --allow-cidr "%WSL_HOST_IP%/32"
echo Proxy started on the WSL2 virtual interface only.
exit /B 0
