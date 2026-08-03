@echo off
REM Compatibility facade: scripts/ops/codex-exec.bat -> scripts/ops/launchers/codex/codex-exec.bat

setlocal EnableExtensions
call "%~dp0launchers\codex\codex-exec.bat" %*
exit /b %errorlevel%
