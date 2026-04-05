@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Launch OpenAI Codex CLI in auto-execution mode
REM Usage: codex-exec.bat "prompt"

if "%~1"=="" (
    echo Usage: codex-exec.bat "prompt"
    echo.
    echo Runs Codex in full-auto mode without confirmations.
    echo Example: codex-exec.bat "refactor ChemBL parser for performance"
    exit /b 1
)

set WSL_DISTRO=Debian
set SCRIPT_DIR=%~dp0

REM Get absolute path
pushd "%SCRIPT_DIR%..\..\" >nul
set REPO_WIN=%cd%
popd >nul

REM Convert to WSL path format
setlocal EnableDelayedExpansion
set "TEMP_PATH=!REPO_WIN:\=/!"
for /f "tokens=1,* delims=:" %%A in ("!TEMP_PATH!") do (
    set "DRIVE=%%A"
    set "REST=%%B"
)
set REPO_WSL=/mnt/!DRIVE!/!REST!

REM Clear problematic PATH
set "PATH=C:\Windows\System32;C:\Windows"

REM Verify Codex is installed
wsl -d %WSL_DISTRO% -- command -v codex >/dev/null 2>&1
if errorlevel 1 (
    echo [codex-launch] ERROR: Codex not found
    echo [codex-launch] Install: npm install -g @openai/codex
    exit /b 1
)

REM Launch in full-auto mode
echo [codex-launch] Prompt: %~1
wsl -d %WSL_DISTRO% -- codex exec --full-auto -C "%REPO_WSL%" "%~1"

exit /b %errorlevel%
