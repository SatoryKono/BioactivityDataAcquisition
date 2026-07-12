[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RenderArgs
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..")).Path
$RenderScript = Join-Path $RepoRoot "docs\02-architecture\diagrams\tooling\render.sh"

$BashCandidates = @()
if ($env:GIT_BASH) {
    $BashCandidates += $env:GIT_BASH
}
$BashCandidates += @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files\Git\usr\bin\bash.exe",
    "bash.exe",
    "bash"
)

$Bash = $null
foreach ($Candidate in $BashCandidates) {
    $Command = Get-Command $Candidate -ErrorAction SilentlyContinue
    if ($Command) {
        $Bash = $Command.Source
        break
    }
}

if (-not $Bash) {
    throw "Git Bash was not found. Install Git for Windows or set GIT_BASH to bash.exe."
}

$RenderScriptForBash = $RenderScript -replace "\\", "/"
& $Bash $RenderScriptForBash @RenderArgs
exit $LASTEXITCODE
