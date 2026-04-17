@echo off
REM Compatibility facade for the canonical Codex launcher

setlocal EnableExtensions
call "%~dp0..\..\..\ai\codex\launch.bat" %*
exit /b %errorlevel%
