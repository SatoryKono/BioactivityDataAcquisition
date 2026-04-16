@echo off
REM Enhanced Codex Auto-Execution Launcher from Windows (via WSL)
REM Runs with full-auto mode (no confirmations)
REM Usage: codex-exec.bat [options] "prompt"

setlocal EnableExtensions

if "%~1"=="" (
    goto :show_help
)

if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%..\..\" >nul || (
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

echo [codex-exec] Prompt: %*
echo [codex-exec] Mode: Auto-execution (full-auto, no confirmations)
echo.

REM Run codex-exec.sh with all arguments
wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/codex-exec.sh" %*

exit /b %errorlevel%

:show_help
echo Codex Auto-Execution Launcher (via WSL)
echo.
echo Usage: codex-exec.bat [options] "prompt"
echo.
echo Options:
echo   --update         Update Codex to latest version
echo   --verbose, -v    Show detailed output
echo   --help, -h       Show this help message
echo.
echo Examples:
echo   codex-exec.bat "refactor ChemBL parser for performance"
echo   codex-exec.bat --update "optimize database queries"
echo.
echo For interactive execution with confirmations, use:
echo   codex.bat "your prompt"
echo.
exit /b 0
