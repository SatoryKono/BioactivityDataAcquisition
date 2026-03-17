@echo off
setlocal EnableExtensions
REM Launch OpenAI Codex CLI (full-auto) through WSL2 Debian.
REM Usage: codex-exec.bat "prompt"

set "REPO_WSL=/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"

if "%~1"=="" (
    echo Usage: codex-exec.bat "prompt"
    echo Runs Codex in full-auto mode, no confirmations.
    exit /b 1
)

wsl -d Debian -- bash -lc "command -v codex"
if errorlevel 1 (
    echo [codex-launch] Codex CLI not found in WSL Debian.
    echo [codex-launch] Install: npm install -g @openai/codex
    exit /b 1
)

wsl -d Debian -- bash -lc "cd \"%REPO_WSL%\" && codex exec --full-auto \"\$@\"" -- %*
