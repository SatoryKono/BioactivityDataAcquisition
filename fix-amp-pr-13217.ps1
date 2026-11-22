# fix-amp-pr-13217.ps1
# PR #13217 (branch docs/amp-orb-surface-13216):
# merge origin/main, resolve the three generated-inventory conflicts by
# regeneration, restore exec bits on the Amp orb hooks, push.
# Run from anywhere inside the local BioETL checkout (Windows PowerShell).
# Stops on the first unexpected failure; unexpected merge conflicts abort
# the script before any commit.

$ErrorActionPreference = 'Stop'

function Invoke-Git {
    param([Parameter(Mandatory)][string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Python {
    param([Parameter(Mandatory)][string[]]$PyArgs)
    & python @PyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "python $($PyArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$root = (& git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0) { throw 'Not inside a git repository.' }
Set-Location $root.Trim()

Invoke-Git @('fetch', 'origin')
Invoke-Git @('checkout', 'docs/amp-orb-surface-13216')
Invoke-Git @('pull')

# The merge is EXPECTED to stop with conflicts in three generated files,
# so its exit code is handled manually instead of via Invoke-Git.
& git merge origin/main
$mergeExit = $LASTEXITCODE

$expected = @(
    'configs/quality/scripts_inventory_manifest.json',
    'docs/reports/generated/documentation-cleanup-inventory.json',
    'docs/reports/generated/documentation-cleanup-inventory.md'
)
$unmerged = @(& git diff --name-only --diff-filter=U)
$unexpected = @($unmerged | Where-Object { $expected -notcontains $_ })
if ($unexpected.Count -gt 0) {
    throw "Unexpected merge conflicts, resolve manually: $($unexpected -join ', ')"
}
if ($mergeExit -ne 0 -and $unmerged.Count -eq 0) {
    throw "git merge failed without listing conflicts (exit code $mergeExit)"
}

if ($unmerged.Count -gt 0) {
    # Generated artifacts: take main's version, then regenerate on the
    # merged tree so both inventories describe the final state.
    Invoke-Git (@('checkout', 'origin/main', '--') + $expected)
    Invoke-Python @('-m', 'scripts.docs', 'generate-cleanup-inventory', '--update')
    Invoke-Python @('-m', 'scripts.engineering.repo', 'check-inventory', '--update',
        '--manifest', 'configs/quality/scripts_inventory_manifest.json')
    # Verify before committing: both inventories must be synchronized.
    Invoke-Python @('-m', 'scripts.docs', 'generate-cleanup-inventory', '--check')
    Invoke-Python @('-m', 'scripts.engineering.repo', 'check-inventory', '--check',
        '--manifest', 'configs/quality/scripts_inventory_manifest.json')
}

Invoke-Git @('add', '-A')
# chmod AFTER add: git add would otherwise overwrite the modes from the
# working tree (both hooks are 0644 on disk under Windows checkouts).
Invoke-Git @('update-index', '--chmod=+x', '.agents/setup')
Invoke-Git @('update-index', '--chmod=+x', '.agents/resume')

$mergeInProgress = Test-Path '.git/MERGE_HEAD'
$staged = @(& git diff --cached --name-only)
if ($mergeInProgress -or $staged.Count -gt 0) {
    Invoke-Git @('commit', '--no-edit')
} else {
    Write-Host 'Nothing to commit.'
}

Invoke-Git @('push')

Write-Host ''
Write-Host 'Done. Final state:'
& git ls-files -s .agents/setup .agents/resume
& git log --oneline -1
