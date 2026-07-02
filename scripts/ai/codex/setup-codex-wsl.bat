@echo off
REM Quick WSL Codex Setup Launcher from Windows
REM This wrapper runs the complete setup script in WSL

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

echo [codex-setup] Starting WSL Codex setup...
echo.

pushd "%SCRIPT_DIR%..\..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

REM Check .env.codex before WSL setup
if not exist "%REPO_WIN%\scripts\ai\codex\.env.codex" (
    echo [WARN] scripts\ai\codex\.env.codex not found
    echo [INFO] Copy the template and add your OpenAI API key:
    echo        copy scripts\ai\codex\.env.codex.example scripts\ai\codex\.env.codex
    echo        notepad scripts\ai\codex\.env.codex
    echo.
)

REM Try to convert path using wslpath
if defined WSL_DISTRO (
    for /f "usebackq delims=" %%I in (`"%WSL_EXE%" -d "%WSL_DISTRO%" -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
) else (
    for /f "usebackq delims=" %%I in (`"%WSL_EXE%" -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"
)

REM If wslpath failed, construct path manually
if not defined REPO_WSL (
    REM Manual conversion: E:\path\to\repo -> /mnt/e/path/to/repo
    for /f "tokens=1" %%A in ("%REPO_WIN%") do (
        set "DRIVE=%%A:="
        set "DRIVE=!DRIVE:~0,1!"
    )

    REM Convert to lowercase
    for %%A in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
        if /i "!DRIVE!"=="%%A" set "DRIVE=%%A"
    )

    REM Build path
    set "PATHPART=%REPO_WIN:~2%"
    set "PATHPART=!PATHPART:\=/!"
    set "REPO_WSL=/mnt/!DRIVE!!PATHPART!"
)

echo [codex-setup] Repository: %REPO_WIN%
echo [codex-setup] WSL path: %REPO_WSL%
echo.

REM Run the complete setup script in WSL
if defined WSL_DISTRO (
    "%WSL_EXE%" -d "%WSL_DISTRO%" -- bash "%REPO_WSL%/scripts/ai/codex/helper/setup-wsl-complete.sh"
) else (
    "%WSL_EXE%" -- bash "%REPO_WSL%/scripts/ai/codex/helper/setup-wsl-complete.sh"
)

if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. See output above for details.
    if /i not "%1" == "/noninteractive" (
        pause
    )
    exit /b %errorlevel%
)

echo.
echo [codex-setup] Complete! You can now use:
echo   - From WSL: ./scripts/ops/launchers/codex/codex.sh
echo   - From WSL: ./scripts/ops/launchers/codex/codex-exec.sh "prompt"
echo   - From Windows: .\scripts\ops\codex.bat
echo   - From Windows: .\scripts\ops\codex-exec.bat "prompt"
echo.
echo For more info: notepad .\scripts\ai\codex\md\POWERSHELL_QUICK_START.md
echo.

if /i not "%1" == "/noninteractive" (
    pause
)
exit /b 0
