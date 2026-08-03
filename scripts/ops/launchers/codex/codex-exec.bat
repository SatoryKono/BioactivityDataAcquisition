@echo off
REM Compatibility facade for the canonical Codex auto-execution launcher

setlocal EnableExtensions
setlocal EnableDelayedExpansion

set "WSL_DISTRO=%BIOETL_WSL_DISTRO%"
set "SCRIPT_DIR=%~dp0"
set "WSL_EXE=wsl"

where wsl >nul 2>nul
if errorlevel 1 (
    if exist "%WINDIR%\System32\wsl.exe" (
        set "WSL_EXE=%WINDIR%\System32\wsl.exe"
    ) else (
        echo [ERROR] WSL executable not found
        echo [INFO] Install WSL or ensure wsl.exe is available from %%WINDIR%%\System32
        exit /b 1
    )
)

if defined WSL_DISTRO (
    "%WSL_EXE%" -d "%WSL_DISTRO%" -- true >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] WSL distro "%WSL_DISTRO%" not found
        echo [INFO] Clear BIOETL_WSL_DISTRO to use the default WSL distro or install it with: wsl --install -d Debian
        exit /b 1
    )
)

pushd "%SCRIPT_DIR%..\..\..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

if defined WSL_DISTRO (
    for /f "usebackq delims=" %%I in (`"%WSL_EXE%" -d "%WSL_DISTRO%" -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
) else (
    for /f "usebackq delims=" %%I in (`"%WSL_EXE%" -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
)

if not defined REPO_WSL (
    set "DRIVE=%REPO_WIN:~0,1%"
    set "PATHPART=%REPO_WIN:~2%"
    set "PATHPART=!PATHPART:\=/!"
    for %%A in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
        if /i "!DRIVE!"=="%%A" set "DRIVE=%%A"
    )
    set "REPO_WSL=/mnt/!DRIVE!!PATHPART!"
)

if not defined REPO_WSL (
    echo [ERROR] Unable to convert repository path for WSL
    exit /b 1
)

if defined WSL_DISTRO (
    "%WSL_EXE%" -d "%WSL_DISTRO%" -- bash "%REPO_WSL%/scripts/ops/launchers/codex/codex-exec.sh" %*
) else (
    "%WSL_EXE%" -- bash "%REPO_WSL%/scripts/ops/launchers/codex/codex-exec.sh" %*
)
exit /b %errorlevel%
