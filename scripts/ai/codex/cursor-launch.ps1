#!/usr/bin/env pwsh
# Cursor / VS Code entrypoint: load non-secret vars from .env.codex, then delegate to WSL launchers.

param(
    [ValidateSet("interactive", "exec", "check", "mcp-setup")]
    [string]$Mode = "interactive",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "../../..")).Path
Set-Location -LiteralPath $RepoRoot

function Import-CodexEnvFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') {
            continue
        }
        if ($line -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            continue
        }

        $name = $matches[1]
        $value = $matches[2].Trim().Trim('"').Trim("'")

        # Keep API keys in WSL only; run-codex-impl.sh sources .env.codex there.
        if ($name -eq "OPENAI_API_KEY") {
            continue
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

Import-CodexEnvFile -Path (Join-Path $ScriptDir ".env.codex")

$CodexBat = Join-Path $RepoRoot "scripts\ops\codex.bat"
$CodexExecBat = Join-Path $RepoRoot "scripts\ops\codex-exec.bat"
$RunCodexPs1 = Join-Path $ScriptDir "run-codex.ps1"

switch ($Mode) {
    "check" {
        & $RunCodexPs1 check
        exit $LASTEXITCODE
    }
    "mcp-setup" {
        & $RunCodexPs1 mcp-setup
        exit $LASTEXITCODE
    }
    "exec" {
        if ($Rest.Count -eq 0) {
            Write-Error "exec mode requires a prompt argument"
            exit 1
        }
        & cmd.exe /c $CodexExecBat @Rest
        exit $LASTEXITCODE
    }
    default {
        if ($Rest.Count -gt 0) {
            & cmd.exe /c $CodexBat @Rest
        }
        else {
            & cmd.exe /c $CodexBat
        }
        exit $LASTEXITCODE
    }
}
