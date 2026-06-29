#!/usr/bin/env pwsh
# Repository root: WSL Codex setup -> scripts/ai/codex/setup-codex-wsl.bat

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupBat = Join-Path $RepoRoot "scripts\ai\codex\setup-codex-wsl.bat"

if (-not (Test-Path -LiteralPath $SetupBat)) {
    Write-Error "Codex WSL setup launcher not found: $SetupBat"
    exit 1
}

& cmd.exe /c "`"$SetupBat`""
exit $LASTEXITCODE
