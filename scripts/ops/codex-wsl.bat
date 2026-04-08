@echo off
REM Modern launcher for Codex from WSL
REM This simply wraps the existing codex.bat script
REM Usage: codex-wsl.bat [prompt]

setlocal EnableExtensions

set WSL_DISTRO=Ubuntu

REM Just delegate to the original codex.bat which handles WSL properly
call "%~dp0codex.bat" %*

exit /b %errorlevel%
