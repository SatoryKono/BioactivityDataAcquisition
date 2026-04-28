#!/usr/bin/env pwsh
# Compatibility launcher for the canonical Vibe surface.

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperDir = Join-Path $ScriptDir "helper"
$CanonicalLauncher = (Join-Path $ScriptDir "..\vibe\launch.ps1")

# Colors
$Colors = @{ Error = "Red"; Warning = "Yellow"; Info = "Cyan" }

function Write-MistralError { Write-Host "[vibe]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " ERROR: $args" }
function Write-MistralWarn { Write-Host "[vibe]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }

if ($Args.Count -gt 0) {
    switch ($Args[0]) {
        "check" {
            & (Join-Path $HelperDir "check-env.ps1")
            exit $LASTEXITCODE
        }
        "setup" {
            & (Join-Path $HelperDir "setup-env.ps1")
            exit $LASTEXITCODE
        }
        "--help" {
            Write-Host "Mistral Vibe Compatibility Launcher"
            Write-Host ""
            Write-Host "Usage: .\run-vibe.ps1 [check|setup|args...]"
            Write-Host "Preferred public entrypoint: python -m scripts.ai vibe [args...]"
            Write-Host "All other arguments are forwarded to scripts/ai/vibe/launch.ps1."
            exit 0
        }
        "-h" {
            Write-Host "Mistral Vibe Compatibility Launcher"
            Write-Host ""
            Write-Host "Usage: .\run-vibe.ps1 [check|setup|args...]"
            Write-Host "Preferred public entrypoint: python -m scripts.ai vibe [args...]"
            Write-Host "All other arguments are forwarded to scripts/ai/vibe/launch.ps1."
            exit 0
        }
    }
}

if (-not (Test-Path $CanonicalLauncher)) {
    Write-MistralError "Canonical Vibe launcher not found: $CanonicalLauncher"
    exit 1
}

& $CanonicalLauncher @Args
exit $LASTEXITCODE
