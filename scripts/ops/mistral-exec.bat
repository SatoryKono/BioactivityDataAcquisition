.\@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Launch Mistral Vibe in prompt mode through WSL
REM Usage: mistral-exec.bat "prompt" [extra vibe flags]

if "%~1"=="" (
    echo Usage: mistral-exec.bat "prompt" [extra vibe flags]
    echo.
    echo Example: mistral-exec.bat "fix the failing architecture test" --max-turns 5
    exit /b 1
)

set "WSL_DISTRO=%BIOETL_WSL_DISTRO%"
if "%WSL_DISTRO%"=="" (
    wsl -d Ubuntu -- bash -lc "exit 0" >nul 2>&1
    if not errorlevel 1 (
        set "WSL_DISTRO=Ubuntu"
    ) else (
        wsl -d Debian -- bash -lc "exit 0" >nul 2>&1
        if not errorlevel 1 (
            set "WSL_DISTRO=Debian"
        )
    )
)
if "%WSL_DISTRO%"=="" (
    echo [mistral-exec] ERROR: No supported WSL distro found. Set BIOETL_WSL_DISTRO explicitly.
    exit /b 1
)

set SCRIPT_DIR=%~dp0

pushd "%SCRIPT_DIR%..\..\" >nul
set REPO_WIN=%cd%
popd >nul

set "TEMP_PATH=!REPO_WIN:\=/!"
for /f "tokens=1,* delims=:" %%A in ("!TEMP_PATH!") do (
    set "DRIVE=%%A"
    set "REST=%%B"
)
for /f %%I in ('powershell -NoProfile -Command "\"!DRIVE!\".ToLowerInvariant()"') do (
    set "DRIVE_LOWER=%%I"
)
set REPO_WSL=/mnt/!DRIVE_LOWER!!REST!

set "PATH=C:\Windows\System32;C:\Windows"

wsl -d %WSL_DISTRO% -- bash -lc "export PATH=\"\$HOME/.local/bin:\$PATH\"; [ -f \"\$HOME/.local/bin/env\" ] && . \"\$HOME/.local/bin/env\" >/dev/null 2>&1 || true; command -v vibe >/dev/null 2>&1"
if errorlevel 1 (
    echo [mistral-exec] ERROR: Mistral Vibe CLI not found in WSL PATH
    echo [mistral-exec] Install with:
    echo [mistral-exec]   curl -LsSf https://mistral.ai/vibe/install.sh ^| bash
    echo [mistral-exec] or
    echo [mistral-exec]   python3 -m pip install --user mistral-vibe
    exit /b 1
)

set "PROMPT=%~1"
shift

echo [mistral-exec] Prompt: %PROMPT%
wsl -d %WSL_DISTRO% -- bash -lc "export PATH=\"\$HOME/.local/bin:\$PATH\"; [ -f \"\$HOME/.local/bin/env\" ] && . \"\$HOME/.local/bin/env\" >/dev/null 2>&1 || true; vibe --workdir \"%REPO_WSL%\" --prompt \"%PROMPT%\" %*"

exit /b %errorlevel%
