#Requires -Version 5.1
<#
.SYNOPSIS
  Install tracked BioETL Grok skills into a Grok skills directory.

.DESCRIPTION
  Root .grok/ is gitignored (machine-local LSP paths). Skill sources are tracked
  under docs/00-project/ai/grok/skills/ and copied here into either:
    - ~/.grok/skills/          (default, user-wide)
    - <repo>/.grok/skills/     (-Project)

.PARAMETER Project
  Install into the repository .grok/skills/ instead of the user profile.

.PARAMETER WhatIf
  Show actions without writing files.

.EXAMPLE
  .\scripts\ai\grok\install_skills.ps1
  .\scripts\ai\grok\install_skills.ps1 -Project
  .\scripts\ai\grok\install_skills.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Project
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$SourceRoot = Join-Path $RepoRoot 'docs\00-project\ai\grok\skills'

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Skill source root not found: $SourceRoot"
}

if ($Project) {
    $DestRoot = Join-Path $RepoRoot '.grok\skills'
} else {
    $DestRoot = Join-Path $env:USERPROFILE '.grok\skills'
}

$skillDirs = Get-ChildItem -LiteralPath $SourceRoot -Directory -ErrorAction Stop |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') }

if (-not $skillDirs) {
    throw "No SKILL.md sources under $SourceRoot"
}

Write-Host "Source: $SourceRoot"
Write-Host "Dest:   $DestRoot"
Write-Host ""

$installed = @()
foreach ($dir in $skillDirs) {
    $name = $dir.Name
    $srcSkill = Join-Path $dir.FullName 'SKILL.md'
    $destDir = Join-Path $DestRoot $name
    $destSkill = Join-Path $destDir 'SKILL.md'

    if ($PSCmdlet.ShouldProcess($destSkill, "Install skill $name")) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item -LiteralPath $srcSkill -Destination $destSkill -Force
        $installed += $name
        Write-Host "OK  $name -> $destSkill"
    }
}

Write-Host ""
Write-Host ("Installed {0} skill(s). Start a new Grok session to rediscover." -f $installed.Count)
if ($Project) {
    Write-Host "Note: .grok/ is gitignored; project install is machine-local only."
}
