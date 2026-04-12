@echo off
setlocal EnableExtensions

REM Launch Codex CLI through WSL2 using the project bootstrap script.

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%..\..\" >nul || (
    echo [codex] ERROR: Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"

if not defined REPO_WSL (
    echo [codex] ERROR: Unable to convert repository path for WSL
    exit /b 1
)

if "%~1"=="" (
    echo [codex] Starting interactive mode...
    wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/codex.sh"
) else (
    echo [codex] Prompt: %*
    wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/codex.sh" %*
)

exit /b %errorlevel%
