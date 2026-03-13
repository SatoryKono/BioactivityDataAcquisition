@echo off
REM Запуск OpenAI Codex CLI (full-auto режим) через WSL2 Debian
REM Использование: codex-exec.bat "prompt"
REM Пример:  codex-exec.bat "fix failing test in test_compound_transformer.py"

set BIOETL_DIR=/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2

if "%~1"=="" (
    echo Usage: codex-exec.bat "prompt"
    echo Runs Codex in full-auto mode (no confirmations).
    exit /b 1
)

wsl -d Debian -- bash -lc "cd %BIOETL_DIR% && codex exec --full-auto '%~1'"
