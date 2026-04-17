@echo off
REM Compatibility facade for the canonical Codex Windows launcher

setlocal EnableExtensions
call "%~dp0..\..\..\ai\codex\launch.bat" %*
exit /b %errorlevel%
