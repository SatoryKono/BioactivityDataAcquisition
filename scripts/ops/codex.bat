@echo off
REM Launch OpenAI Codex CLI (interactive) through WSL2 Debian.
REM Usage: codex.bat [prompt]
REM Example: codex.bat "add unit test for compound transformer"

set BIOETL_DIR=/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2

if "%~1"=="" (
    wsl -d Debian -- bash -lc "cd %BIOETL_DIR% && codex"
) else (
    wsl -d Debian -- bash -lc "cd %BIOETL_DIR% && codex '%~1'"
)
