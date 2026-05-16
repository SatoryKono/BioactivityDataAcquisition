Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
Set-Location $RepoRoot

$Bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $Bash) {
    Write-Error "[pretest_guardrails.ps1][error] bash is not available."
    exit 1
}

& $Bash.Source "scripts/engineering/dev/pretest_guardrails.sh" @args
exit $LASTEXITCODE
