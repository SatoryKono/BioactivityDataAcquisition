@echo off
setlocal EnableExtensions
REM Launch OpenAI Codex CLI (interactive) through WSL2 Debian.
REM Usage:
REM   codex.bat
REM   codex.bat "add unit test for compound transformer"

set "REPO_WSL=/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"

wsl -d Debian -- bash -lc "command -v codex"
if errorlevel 1 (
    echo [codex-launch] Codex CLI not found in WSL Debian.
    echo [codex-launch] Install: npm install -g @openai/codex
    exit /b 1
)

if "%~1"=="" goto interactive
wsl -d Debian -- bash -lc "cd \"%REPO_WSL%\" && codex \"\$@\"" -- %*
exit /b %errorlevel%

:interactive
wsl -d Debian -- bash -lc "cd \"%REPO_WSL%\" && codex"
exit /b %errorlevel%
