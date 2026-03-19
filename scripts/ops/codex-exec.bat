@echo off
setlocal EnableExtensions
REM Launch OpenAI Codex CLI (full-auto) through WSL2 Debian.
REM Usage: codex-exec.bat "prompt"

set "WSL_DISTRO=Debian"
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_WIN=%%~fI"

for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
if not defined REPO_WSL (
    echo [codex-launch] Unable to resolve repo path in WSL: %REPO_WIN%
    exit /b 1
)

if "%~1"=="" (
    echo Usage: codex-exec.bat "prompt"
    echo Runs Codex in full-auto mode, no confirmations.
    exit /b 1
)

wsl -d %WSL_DISTRO% -- bash -lc "command -v codex >/dev/null 2>&1"
if errorlevel 1 (
    echo [codex-launch] Codex CLI not found in WSL Debian.
    echo [codex-launch] Install: npm install -g @openai/codex
    exit /b 1
)

wsl -d %WSL_DISTRO% -- bash -lc "exec codex exec --full-auto -C \"\$1\" \"\${@:2}\"" -- "%REPO_WSL%" %*
