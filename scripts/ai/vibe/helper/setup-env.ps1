#!/usr/bin/env pwsh
# Helper: Setup Mistral Vibe environment by delegating to WSL bash.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupScript = Join-Path $ScriptDir "setup-env.sh"

wsl -e bash -- $SetupScript
exit $LASTEXITCODE
