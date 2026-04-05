@echo off
REM Quick start for Codex with automatic setup
REM Usage: start-codex.bat [prompt]

setlocal EnableExtensions

echo ========================================
echo  Codex Setup & Launch
echo ========================================
echo.

REM Step 1: Ensure WSL VPN is configured
echo [1] Ensuring WSL VPN configuration...
$env:PATH = "C:\Windows\System32;C:\Windows"; wsl -d Debian -- bash -c "grep -q '172.26.16.1' /etc/resolv.conf 2>/dev/null || echo 'nameserver 172.26.16.1' | sudo tee /etc/resolv.conf > /dev/null"
if errorlevel 1 (
    echo [!] WARNING: Could not configure WSL VPN. OpenAI API may not be accessible.
) else (
    echo [OK] WSL VPN configured
)
echo.

REM Step 2: Launch Codex
echo [2] Launching Codex CLI...
if "%~1"=="" (
    echo [codex] Interactive mode
    call "%~dp0codex.bat"
) else (
    echo [codex] With prompt: %~1
    call "%~dp0codex.bat" "%~1"
)

exit /b %errorlevel%
