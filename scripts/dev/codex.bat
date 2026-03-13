@echo off
REM Запуск OpenAI Codex CLI (интерактивный режим) через WSL2 Debian
REM Использование: codex.bat [prompt]
REM Пример:  codex.bat "add unit test for compound transformer"

set BIOETL_DIR=/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2

if "%~1"=="" (
    wsl -d Debian -- bash -lc "cd %BIOETL_DIR% && codex"
) else (
    wsl -d Debian -- bash -lc "cd %BIOETL_DIR% && codex '%~1'"
)
