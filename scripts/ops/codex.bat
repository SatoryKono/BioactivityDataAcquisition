@echo off
REM Enhanced Codex Launcher from Windows (via WSL)
REM Supports interactive and auto-execution modes with improved error handling
REM Usage: codex.bat [options] [prompt]

setlocal EnableExtensions

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

REM Construct arguments for WSL bash
setlocal DisableDelayedExpansion
set ARGS=%*
setlocal EnableDelayedExpansion

if "!ARGS!"=="" (
    echo [codex] Starting interactive mode...
    wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/codex.sh"
) else (
    echo [codex] Arguments: !ARGS!
    wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ops/codex.sh" !ARGS!
)

exit /b %errorlevel%

:show_help
echo Codex CLI Launcher (via WSL)
echo.
echo Usage: codex.bat [options] [prompt]
echo.
echo Options:
echo   --update         Update Codex to latest version
echo   --verbose, -v    Show detailed output
echo   --help, -h       Show this help message
echo.
echo Examples:
echo   codex.bat
echo   codex.bat "analyze the pipeline structure"
echo   codex.bat --update "refactor the parser"
echo.
echo For auto-execution without confirmations, use:
echo   codex-exec.bat "your prompt"
echo.
exit /b 0
