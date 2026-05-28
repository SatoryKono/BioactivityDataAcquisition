Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
Set-Location $RepoRoot

$Bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $Bash) {
    if ($env:BIOETL_PREFLIGHT_REQUIRE_BASH -eq "1") {
        Write-Error "[pretest_guardrails.ps1][error] bash is not available."
        exit 1
    }
    Write-Warning "[pretest_guardrails.ps1][warn] bash is not available; skipping pretest guardrails."
    exit 0
}

& $Bash.Source "scripts/engineering/dev/pretest_guardrails.sh" @args
exit $LASTEXITCODE
