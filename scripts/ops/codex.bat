@echo off
REM Compatibility facade: scripts/ops/codex.bat -> scripts/ops/launchers/codex/codex.bat

setlocal EnableExtensions
call "%~dp0launchers\codex\codex.bat" %*
exit /b %errorlevel%
