@echo off
setlocal EnableExtensions

REM Launch Codex CLI through WSL2
REM Codex will use the current working directory context

set WSL_DISTRO=Ubuntu
set "PATH=C:\Windows\System32;C:\Windows"

REM Check Codex is installed
wsl -d %WSL_DISTRO% -- command -v codex >/dev/null 2>&1
if errorlevel 1 (
    echo [ERROR] Codex CLI not found
    echo [INFO] Install: npm install -g @openai/codex
    exit /b 1
)

REM Launch Codex
REM Note: Without -C flag, Codex uses user's default working directory
REM For best results, run from project root or specify directory via --add-dir
if "%~1"=="" (
    echo [codex] Starting interactive mode...
    wsl -d %WSL_DISTRO% -- codex
) else (
    echo [codex] Prompt: %*
    wsl -d %WSL_DISTRO% -- codex %*
)

exit /b %errorlevel%
