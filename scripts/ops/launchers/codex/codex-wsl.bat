@echo off
REM Compatibility facade for the canonical Codex Windows launcher

setlocal EnableExtensions
call "%~dp0codex.bat" %*
exit /b %errorlevel%
