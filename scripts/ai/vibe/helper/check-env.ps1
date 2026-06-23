#!/usr/bin/env pwsh
# Helper: Check Mistral Vibe environment by delegating to WSL bash.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CheckScript = Join-Path $ScriptDir "check-env.sh"

wsl -e bash -- $CheckScript
exit $LASTEXITCODE
