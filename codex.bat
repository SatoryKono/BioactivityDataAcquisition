@echo off
REM Root CMD compatibility shim for the primary PowerShell launcher.
REM Usage: codex.bat [command] [prompt...]

setlocal enabledelayedexpansion

set "LAUNCHER=%~dp0codex.ps1"

if not exist "%LAUNCHER%" (
    echo [ERROR] Codex launcher not found at: %LAUNCHER%
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER%" %*
exit /b %ERRORLEVEL%
