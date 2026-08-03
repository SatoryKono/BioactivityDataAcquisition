# Compatibility wrapper for the legacy root Docker setup launcher.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$Target = Join-Path $PSScriptRoot "ops/docker-setup.ps1"
if (-not (Test-Path $Target)) {
    Write-Error "Missing canonical Docker setup script: $Target"
    exit 1
}

& $Target @Args
exit $LASTEXITCODE
