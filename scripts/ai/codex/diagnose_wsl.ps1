# Canonical Codex WSL diagnostic launcher from Windows.

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════════════════╗"
Write-Host "║  Codex WSL Diagnostic Tool (from Windows)          ║"
Write-Host "╚════════════════════════════════════════════════════╝"
Write-Host ""

$wslDistro = "Ubuntu"
Write-Host "[diagnose] Checking WSL distro..."

try {
    $distros = wsl --list --quiet 2>$null | Select-Object -First 1
    if ($distros) {
        $wslDistro = $distros.Trim()
        Write-Host "[OK] WSL Distro: $wslDistro" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] Could not detect WSL distro, using default: $wslDistro" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[diagnose] Converting paths and running diagnostic..."
Write-Host ""

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Write-Host "[diagnose] Repository: $repoRoot" -ForegroundColor Cyan

try {
    $repoWSL = wsl -d $wslDistro -- wslpath -a $repoRoot
    Write-Host "[diagnose] WSL Path: $repoWSL" -ForegroundColor Cyan
} catch {
    Write-Host "[ERROR] Failed to convert path to WSL: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

$diagnosticScript = "$repoWSL/scripts/ai/codex/diagnose_wsl.sh"
if ($Verbose) {
    Write-Host "[diagnose] Running: wsl -d $wslDistro -- bash $diagnosticScript" -ForegroundColor Blue
    Write-Host ""
}

wsl -d $wslDistro -- bash $diagnosticScript
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "[OK] Diagnostic completed successfully" -ForegroundColor Green
} else {
    Write-Host "[WARN] Diagnostic completed with warnings or errors (exit code: $exitCode)" -ForegroundColor Yellow
}

exit $exitCode
