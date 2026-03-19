@echo off
setlocal EnableExtensions
REM Launch OpenAI Codex CLI (interactive) through WSL2 Debian.
REM Usage:
REM   codex.bat
REM   codex.bat "add unit test for compound transformer"

set "WSL_DISTRO=Debian"
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_WIN=%%~fI"

for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
if not defined REPO_WSL (
    echo [codex-launch] Unable to resolve repo path in WSL: %REPO_WIN%
    exit /b 1
)

wsl -d %WSL_DISTRO% -- bash -lc "command -v codex >/dev/null 2>&1"
if errorlevel 1 (
    echo [codex-launch] Codex CLI not found in WSL Debian.
    echo [codex-launch] Install: npm install -g @openai/codex
    exit /b 1
)

if "%~1"=="" goto interactive
wsl -d %WSL_DISTRO% -- bash -lc "exec codex -C \"\$1\" \"\${@:2}\"" -- "%REPO_WSL%" %*
exit /b %errorlevel%

:interactive
wsl -d %WSL_DISTRO% -- bash -lc "exec codex -C \"\$1\"" -- "%REPO_WSL%"
exit /b %errorlevel%
