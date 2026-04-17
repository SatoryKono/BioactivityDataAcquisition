@echo off
REM Compatibility facade for the canonical Codex auto-execution launcher

setlocal EnableExtensions

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%..\..\..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"

if not defined REPO_WSL (
    echo [ERROR] Unable to convert repository path for WSL
    exit /b 1
)

wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/launchers/codex/codex-exec.sh" %*
exit /b %errorlevel%
