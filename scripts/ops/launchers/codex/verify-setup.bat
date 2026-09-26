@echo off
REM Compatibility facade for the canonical Codex setup verification launcher

setlocal EnableExtensions
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-setup.ps1" %*
exit /b %errorlevel%
