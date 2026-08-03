@echo off
REM Install user-level Windows command shims for the BioETL Codex launchers.

setlocal EnableExtensions
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-codex-cmd.ps1" %*
exit /b %errorlevel%
