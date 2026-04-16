@echo off
REM Codex Setup Verification Launcher
REM Recommends PowerShell for better output
REM Usage: .\scripts\ops\verify-setup.bat

setlocal EnableExtensions
setlocal EnableDelayedExpansion

echo.
echo =========================================================
echo  Codex Setup Verification
echo =========================================================
echo.
echo Tip: For better formatting, use PowerShell:
echo   .\scripts\ops\verify-setup.ps1
echo.

set "WSL_DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%..\..\" >nul || (
    echo [ERROR] Unable to resolve repository root
    pause
    exit /b 1
)
set "REPO_WIN=%CD%"
popd >nul

REM Try to convert path using wslpath
echo [verify] Converting paths for WSL...
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
    
    echo [OK] Repository path: !REPO_WSL! (constructed)
) else (
    echo [OK] Repository path: %REPO_WSL%
)

echo.
echo [verify] Running diagnostic tool...
echo.

wsl -d %WSL_DISTRO% -- bash "!REPO_WSL!/scripts/ops/diagnose-codex-wsl.sh" 2>&1

set "DIAG_EXIT=%ERRORLEVEL%"

echo.
if %DIAG_EXIT% equ 0 (
    echo =========================================================
    echo  All Checks Passed! System is ready.
    echo =========================================================
    echo.
    echo Next steps:
    echo   1. Run setup if not already done:
    echo      .\script-codex\setup-codex-wsl.bat
    echo.
    echo   2. Test Codex:
    echo      .\scripts\ops\codex.bat "analyze the pipeline"
    echo.
    echo   3. View documentation:
    echo      notepad .\scripts\ops\POWERSHELL_QUICK_START.md
    echo.
) else (
    echo =========================================================
    echo  Some Issues Found (see above)
    echo =========================================================
    echo.
    echo Run setup to fix:
    echo   .\script-codex\setup-codex-wsl.bat
    echo.
)

pause
exit /b %DIAG_EXIT%
