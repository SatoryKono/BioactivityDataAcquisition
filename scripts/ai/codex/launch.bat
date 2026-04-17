@echo off
REM Canonical Codex launcher from Windows (via WSL)

setlocal EnableExtensions

if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%..\..\..\" >nul || (
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

setlocal DisableDelayedExpansion
set ARGS=%*
setlocal EnableDelayedExpansion

if "!ARGS!"=="" (
    echo [codex] Starting interactive mode...
    wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ai/codex/launch.sh"
) else (
    echo [codex] Arguments: !ARGS!
    wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/scripts/ai/codex/launch.sh" !ARGS!
)

exit /b %errorlevel%

:show_help
echo Codex CLI Launcher (via WSL)
echo.
echo Usage: launch.bat [options] [prompt]
echo.
echo Options:
echo   --update         Update Codex to latest version
echo   --verbose, -v    Show detailed output
echo   --help, -h       Show this help message
echo.
echo Examples:
echo   launch.bat
echo   launch.bat "analyze the pipeline structure"
echo   launch.bat --update "refactor the parser"
echo.
echo For auto-execution without confirmations, use:
echo   exec.bat "your prompt"
echo.
exit /b 0
