@echo off
REM Codex WSL Diagnostic Tool Launcher (from Windows)
REM Run from PowerShell: .\scripts\ops\diagnose-codex-wsl.bat

setlocal EnableExtensions

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

echo [diagnose] Initializing diagnostic tool...
echo.

pushd "%SCRIPT_DIR%..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

echo [diagnose] Repository: %REPO_WIN%

for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"

if not defined REPO_WSL (
    echo [ERROR] Unable to convert repository path for WSL
    exit /b 1
)

echo [diagnose] WSL Path: %REPO_WSL%
echo.
echo [diagnose] Running diagnostic checks...
echo.

REM Run diagnostic script in WSL
wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/diagnose-codex-wsl.sh"

exit /b %errorlevel%
