@echo off
REM Compatibility facade for the canonical Codex auto-execution launcher

setlocal EnableExtensions
call "%~dp0..\..\..\ai\codex\exec.bat" %*
exit /b %errorlevel%
