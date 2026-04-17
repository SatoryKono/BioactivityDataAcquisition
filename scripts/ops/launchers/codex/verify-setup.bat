@echo off
REM Compatibility facade for the canonical Codex setup verification launcher

setlocal EnableExtensions
call "%~dp0..\..\..\ai\codex\verify_setup.bat" %*
exit /b %errorlevel%
