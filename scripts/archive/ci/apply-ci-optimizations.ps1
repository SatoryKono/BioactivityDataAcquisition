<#
Compatibility wrapper for canonical script.

Canonical script:
- scripts/ci/apply-ci-optimizations.ps1
#>
n# Build canonical path correctly (single child path)
$canonical = Join-Path $PSScriptRoot 'ci\apply-ci-optimizations.ps1'
if (-not (Test-Path $canonical)) {
    Write-Error "ERROR: canonical script not found: $canonical"
    exit 2
}
& $canonical @args
