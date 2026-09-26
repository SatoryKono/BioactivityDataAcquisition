@echo off
REM Quick WSL Gemini setup launcher from Windows.
REM This wrapper runs the canonical Gemini setup command inside WSL.

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
        echo [INFO] Clear BIOETL_WSL_DISTRO to use the default WSL distro or install the named distro.
        exit /b 1
    )
)

echo [gemini-setup] Starting WSL Gemini setup...
echo.

pushd "%SCRIPT_DIR%..\..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

if not exist "%REPO_WIN%\scripts\ai\gemini\.env.gemini" (
    echo [WARN] scripts\ai\gemini\.env.gemini not found
    echo [INFO] Create it manually with GEMINI_API_KEY before running Gemini.
    echo [INFO] To generate a local template explicitly, rerun setup with BIOETL_CREATE_LOCAL_ENV_FILES=1.
    echo.
)

REM Try to convert path using wslpath.
if defined WSL_DISTRO (
    for /f "usebackq delims=" %%I in (`"%WSL_EXE%" -d "%WSL_DISTRO%" -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
) else (
    for /f "usebackq delims=" %%I in (`"%WSL_EXE%" -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
)

REM If wslpath failed, construct path manually: E:\repo -> WSL /mnt/<drive>/repo.
if not defined REPO_WSL (
    for /f "tokens=1" %%A in ("%REPO_WIN%") do (
        set "DRIVE=%%A:="
        set "DRIVE=!DRIVE:~0,1!"
    )

    for %%A in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
        if /i "!DRIVE!"=="%%A" set "DRIVE=%%A"
    )

    set "PATHPART=%REPO_WIN:~2%"
    set "PATHPART=!PATHPART:\=/!"
    set "REPO_WSL=/mnt/!DRIVE!!PATHPART!"
)

echo [gemini-setup] Repository: %REPO_WIN%
echo [gemini-setup] WSL path: %REPO_WSL%
echo.

if defined WSL_DISTRO (
    "%WSL_EXE%" -d "%WSL_DISTRO%" -- bash "%REPO_WSL%/scripts/ai/gemini/run-gemini.sh" setup
) else (
    "%WSL_EXE%" -- bash "%REPO_WSL%/scripts/ai/gemini/run-gemini.sh" setup
)

if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. See output above for details.
    if /i not "%1" == "/noninteractive" (
        pause
    )
    exit /b %errorlevel%
)

if defined WSL_DISTRO (
    "%WSL_EXE%" -d "%WSL_DISTRO%" -- bash "%REPO_WSL%/scripts/ai/gemini/run-gemini.sh" mcp-check
) else (
    "%WSL_EXE%" -- bash "%REPO_WSL%/scripts/ai/gemini/run-gemini.sh" mcp-check
)

if errorlevel 1 (
    echo.
    echo [ERROR] MCP check failed. See output above for details.
    if /i not "%1" == "/noninteractive" (
        pause
    )
    exit /b %errorlevel%
)

echo.
echo [gemini-setup] Complete! You can now use:
echo   - From WSL: bash scripts/ai/gemini/run-gemini.sh
echo   - From Windows: .\scripts\ai\gemini\run-gemini.ps1
echo   - From Windows: .\scripts\ai\gemini\launch-gemini-wsl.ps1
echo.
echo Run .\scripts\ai\gemini\run-gemini.ps1 check after configuring scripts\ai\gemini\.env.gemini.
echo.

if /i not "%1" == "/noninteractive" (
    pause
)
exit /b 0
