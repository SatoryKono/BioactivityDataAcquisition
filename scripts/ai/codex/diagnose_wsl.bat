@echo off
REM Canonical Windows transport for Codex WSL diagnostics

setlocal EnableExtensions
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnose_wsl.ps1" %*
exit /b %errorlevel%
