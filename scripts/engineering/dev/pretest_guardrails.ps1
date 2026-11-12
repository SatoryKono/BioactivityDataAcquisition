Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
Set-Location $RepoRoot

$Bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $Bash) {
    Write-Error -ErrorAction Continue "[pretest_guardrails.ps1][error] Required bash is unavailable; no preflight PASS. Install/select Git Bash or the qualified WSL runtime."
    exit 2
}

& $Bash.Source "scripts/engineering/dev/pretest_guardrails.sh" @args
exit $LASTEXITCODE
