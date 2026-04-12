@echo off
setlocal EnableExtensions

REM Launch OpenAI Codex CLI in auto-execution mode through the project WSL wrapper.
REM Usage: codex-exec.bat "prompt"

if "%~1"=="" (
    echo Usage: codex-exec.bat "prompt"
    echo.
    echo Runs Codex in full-auto mode without confirmations.
    echo Example: codex-exec.bat "refactor ChemBL parser for performance"
    exit /b 1
)

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%..\..\" >nul || (
    echo [codex-launch] ERROR: Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"

if not defined REPO_WSL (
    echo [codex-launch] ERROR: Unable to convert repository path for WSL
    exit /b 1
)

echo [codex-launch] Prompt: %*
wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/codex-exec.sh" %*

exit /b %errorlevel%
