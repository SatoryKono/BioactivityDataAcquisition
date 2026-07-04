@echo off
REM Repository root: WSL Codex setup -> scripts/ai/codex/setup-codex-wsl.bat

setlocal EnableExtensions
call "%~dp0scripts\ai\codex\setup-codex-wsl.bat"
exit /b %errorlevel%
