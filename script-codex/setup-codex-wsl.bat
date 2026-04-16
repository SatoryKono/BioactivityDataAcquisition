@echo off
REM Quick WSL Codex Setup Launcher from Windows
REM This wrapper runs the complete setup script in WSL

setlocal EnableExtensions
setlocal EnableDelayedExpansion

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

echo [codex-setup] Starting WSL Codex setup...
echo.

pushd "%SCRIPT_DIR%..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

REM Try to convert path using wslpath
for /f "usebackq delims=" %%I in (`wsl -d %WSL_DISTRO% -- wslpath -a "%REPO_WIN%" 2^>nul`) do set "REPO_WSL=%%I"

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
wsl -d %WSL_DISTRO% -- bash "%REPO_WSL%/script-codex/helper/setup-wsl-complete.sh"

if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. See output above for details.
    pause
    exit /b %errorlevel%
)

echo.
echo [codex-setup] Complete! You can now use:
echo   - From WSL: ./scripts/ops/codex.sh
echo   - From WSL: ./scripts/ops/codex-exec.sh "prompt"
echo   - From Windows: .\scripts\ops\codex.bat
echo   - From Windows: .\scripts\ops\codex-exec.bat "prompt"
echo.
echo For more info: notepad .\script-codex\md\POWERSHELL_QUICK_START.md
echo.

pause
exit /b 0
