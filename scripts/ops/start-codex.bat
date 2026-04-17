@echo off
REM Compatibility facade for the canonical Codex Windows launcher
REM Usage: start-codex.bat [prompt]

setlocal EnableExtensions

echo ========================================
echo  Codex Setup & Launch
echo ========================================
echo.
echo [compat] Delegating to scripts\ai\codex\launch.bat
echo.

call "%~dp0..\ai\codex\launch.bat" %*
exit /b %errorlevel%
