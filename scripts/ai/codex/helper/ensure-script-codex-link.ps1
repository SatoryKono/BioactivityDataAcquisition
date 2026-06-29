#!/usr/bin/env pwsh
# Create a local script-codex junction -> scripts/ai/codex for backward-compatible paths.

param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
}

$Target = Join-Path $RepoRoot "scripts\ai\codex"
$Link = Join-Path $RepoRoot "script-codex"

if (-not (Test-Path -LiteralPath $Target)) {
    Write-Error "Canonical Codex directory not found: $Target"
    exit 1
}

if (Test-Path -LiteralPath $Link) {
    $item = Get-Item -LiteralPath $Link -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Host "[ok] script-codex link already exists: $Link"
        exit 0
    }
    Write-Warning "script-codex exists but is not a junction; skipping automatic link creation"
    exit 0
}

Write-Host "[codex-setup] Creating script-codex junction -> scripts/ai/codex"
cmd.exe /c "mklink /J `"$Link`" `"$Target`""
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not create script-codex junction (non-fatal)"
    exit 0
}

Write-Host "[ok] script-codex junction created"
exit 0
