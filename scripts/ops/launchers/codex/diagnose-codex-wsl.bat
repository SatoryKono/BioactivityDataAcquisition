@echo off
REM Compatibility facade for the canonical Codex WSL diagnostic launcher

setlocal EnableExtensions
call "%~dp0..\..\..\ai\codex\diagnose_wsl.bat" %*
exit /b %errorlevel%
