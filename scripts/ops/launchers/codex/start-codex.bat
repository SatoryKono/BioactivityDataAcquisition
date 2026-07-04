@echo off
REM Compatibility facade for the canonical Codex Windows launcher
REM Usage: start-codex.bat [prompt]

setlocal EnableExtensions

echo ========================================
echo  Codex Setup & Launch
echo ========================================
echo.
echo [compat] Delegating to scripts\ops\launchers\codex\codex.bat
echo.

call "%~dp0codex.bat" %*
exit /b %errorlevel%
