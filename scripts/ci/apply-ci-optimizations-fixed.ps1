<#
apply-ci-optimizations-fixed.ps1

Scans .github/workflows, suggests CI optimizations and optionally applies them:
 - Adds top-level concurrency block if missing
 - Adds paths-ignore under push/pull_request triggers if missing
 - Creates a reusable setup workflow (.github/workflows/reusable-setup.yml)
 - Writes a report to reports/ci_optimization_report.txt and backs up modified workflows
 - If run with -Apply, creates a new git branch, commits changes and optionally pushes (requires git and repo remote access)

Usage examples:
  .\apply-ci-optimizations-fixed.ps1               # dry run, produce report and suggested changes written locally
  .\apply-ci-optimizations-fixed.ps1 -Apply        # apply changes and commit on a new branch locally
  .\apply-ci-optimizations-fixed.ps1 -Apply -Push  # apply, commit and push branch to origin (requires credentials)

Note: Run from repository root. This script avoids changing branch protection or org-level settings.
#>

[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$Push,
    [string]$BranchPrefix = "ci/optimize-workflows",
    [string]$RepoRoot = ".",
    [string]$CommitMessage = "chore(ci): add concurrency and path-filters to workflows; add reusable setup`n`nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
    [string]$BackupDir = "reports\workflow_backups",
    [string]$ReportFile = "reports\ci_optimization_report.txt"
)

Set-StrictMode -Version Latest

Write-Host "Repo root: $RepoRoot"
$workflowsDir = Join-Path $RepoRoot ".github\workflows"
if (-not (Test-Path $workflowsDir)) { Write-Error ".github\workflows not found under $RepoRoot"; exit 1 }

$pathIgnoreList = @(
  "docs/**",
  "*.md",
  ".ai/**",
  ".claude/**",
  ".github/workflows/**",
  "LICENSE"
)

function Make-Indent($n) { if ($n -le 0) { return "" } else { return -join (1..$n | ForEach-Object { ' ' }) } }

function Get-IndentLen($line) { if ($line -match '^( *)') { return $matches[1].Length } else { return 0 } }

$changed = @()
$report = @()
# ensure backup dir exists
$backupPath = Join-Path $RepoRoot $BackupDir
New-Item -ItemType Directory -Force -Path $backupPath | Out-Null

# process each yaml file
Get-ChildItem -Path $workflowsDir -Filter *.yml -File | ForEach-Object {
  $file = $_.FullName
  $report += "Processing: $file"
  $origContent = Get-Content -Raw -Encoding UTF8 -Path $file
  $lines = [regex]::Split($origContent, "\r?\n")
  $originalLines = $lines.Clone()
  $modified = $false

  # add concurrency if missing
  if (-not ($origContent -match '(?m)^\s*concurrency\s*:')) {
     # find index after 'name:' or before 'on:'
     $insertIndex = $null
     for ($i=0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -match '^\s*name\s*:') { $insertIndex = $i+1; break }
     }
     if ($insertIndex -eq $null) {
        for ($i=0; $i -lt $lines.Length; $i++) { if ($lines[$i] -match '^\s*on\s*:') { $insertIndex = $i; break } }
     }
     if ($insertIndex -eq $null) { $insertIndex = 0 }

     $concLines = @(
       'concurrency:',
       '  group: ${{ github.workflow }}-${{ github.ref }}',
       '  cancel-in-progress: true'
     )

     if ($insertIndex -eq 0) {
        $lines = $concLines + $lines
     } else {
        $prefix = $lines[0..($insertIndex-1)]
        $suffix = $lines[$insertIndex..($lines.Length - 1)]
        $lines = $prefix + $concLines + $suffix
     }
     $modified = $true
     $report += " - Added concurrency block"
  } else {
     $report += " - concurrency already present"
  }

  # add paths-ignore under push/pull_request if missing
  for ($j=0; $j -lt $lines.Length; $j++) {
     if ($lines[$j] -match '^\s*(push|pull_request)\s*:\s*$') {
        $trigger = $matches[1]
        $indent = Get-IndentLen $lines[$j]
        # scan children lines
        $hasPathsIgnore = $false
        for ($k = $j+1; $k -lt $lines.Length; $k++) {
           $line = $lines[$k]
           if ($line.Trim() -eq '') { continue }
           $lineIndent = Get-IndentLen $line
           if ($lineIndent -le $indent) { break }
           if ($line.TrimStart() -match '^paths-ignore\s*:') { $hasPathsIgnore = $true; break }
        }
        if (-not $hasPathsIgnore) {
           $childIndent = Make-Indent($indent + 2)
           $block = @()
           $block += ($childIndent + 'paths-ignore:')
           foreach ($p in $pathIgnoreList) { $block += ($childIndent + "  - '$p'") }
           # insert after $j line
           if ($j -eq ($lines.Length -1)) {
              $lines += $block
           } else {
              $prefix = $lines[0..$j]
              if ($j+1 -le $lines.Length -1) {
                 $suffix = $lines[($j+1)..($lines.Length - 1)]
              } else { $suffix = @() }
              $lines = $prefix + $block + $suffix
           }
           $modified = $true
           $report += " - Added paths-ignore under $trigger"
           # advance index to skip newly inserted block
           $j += $block.Length
        } else {
           $report += " - $trigger already has paths-ignore"
        }
     }
  }

  if ($modified) {
     # save backup
     $bakName = [System.IO.Path]::Combine($backupPath, ([System.IO.Path]::GetFileName($file) + '.' + (Get-Date -Format yyyyMMddHHmmss) + '.bak'))
     Set-Content -Path $bakName -Value ($originalLines -join "`n") -Encoding UTF8
     # write modified file
     Set-Content -Path $file -Value ($lines -join "`n") -Encoding UTF8
     $changed += $file
     $report += " - File modified and backed up to $bakName"
  } else {
     $report += " - No changes required"
  }

  $report += ""
}

# create reusable workflow file
$reusablePath = Join-Path $workflowsDir 'reusable-setup.yml'
if (-not (Test-Path $reusablePath)) {
   $reusableContent = @'
name: Reusable CI setup

on:
  workflow_call:
    inputs:
      python-version:
        required: false
        default: "3.11"

jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      python-version: ${{ inputs.python-version }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}

      - name: Cache uv and virtualenv
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/uv
            .venv
          key: uv-${{ runner.os }}-py${{ inputs.python-version }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-py${{ inputs.python-version }}-

      - name: Install uv
        uses: astral-sh/setup-uv@v7
'@
   Set-Content -Path $reusablePath -Value $reusableContent -Encoding UTF8
   $changed += $reusablePath
   $report += "Created reusable workflow: $reusablePath"
} else {
   $report += "Reusable workflow already exists: $reusablePath"
}

# write report
$reportHeader = @()
$reportHeader += "CI Optimization report - $(Get-Date -Format u)"
$reportHeader += "Repo root: $RepoRoot"
$reportHeader += ""
$reportHeader += $report
New-Item -ItemType Directory -Force -Path (Split-Path -Path (Join-Path $RepoRoot $ReportFile) -Parent) | Out-Null
Set-Content -Path (Join-Path $RepoRoot $ReportFile) -Value ($reportHeader -join "`n") -Encoding UTF8
Write-Host "Report written to $ReportFile"

if ($Apply) {
  # commit changes to new branch
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
     Write-Error "git not found: cannot create branch/commit. Changes are written to files but not committed."
     exit 1
  }

  $ts = Get-Date -Format yyyyMMddHHmmss
  $branch = "$BranchPrefix-$ts"
  git checkout -b $branch
  foreach ($f in $changed) { git add -- $f }
  # ensure commit message includes co-author trailer
  $finalCommitMsg = $CommitMessage
  git commit -m $finalCommitMsg
  Write-Host "Committed changes on branch $branch"
  if ($Push) {
     git push -u origin $branch
     Write-Host "Pushed branch $branch to origin"
  } else {
     Write-Host "Run: git push -u origin $branch to push the branch"
  }
} else {
  Write-Host "Dry run complete. To apply changes, re-run with -Apply (and -Push to push the created branch)."
}

Write-Host "Done."
