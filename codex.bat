@echo off
REM Quick launcher for Codex from Windows CMD
REM Usage: codex.bat [command] [prompt...]

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0scripts\ai\codex"
set "LAUNCHER=%SCRIPT_DIR%\run-codex.ps1"

if not exist "%LAUNCHER%" (
    echo [ERROR] Codex launcher not found at: %LAUNCHER%
    exit /b 1
)

REM PowerShell invocation
powershell -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER%" %*
exit /b %ERRORLEVEL%
