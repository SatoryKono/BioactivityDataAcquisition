#Requires -Version 5.1
<#
.SYNOPSIS
  Prepare BioETL nine-domain audit workflows: render operator prompts into a run folder.

.DESCRIPTION
  Renders the nine library audit cards (+ architecture.review) via scripts.ai.prompts
  into reports/audit-runs/<run_id>/prompts/ for paste into Grok/Codex/Junie, or as
  inputs to the nine-domain-audit Rhai workflow.

  Domains (canonical prompt ids):
    docs-content, tests-system, tech-debt, repo-tree, github-actions,
    agents-runtime, diagrams, docs-pipeline, architecture.review

  Does NOT run the audits. Mutation flags default false.

.EXAMPLE
  .\scripts\ai\grok\prepare_nine_domain_audits.ps1
  .\scripts\ai\grok\prepare_nine_domain_audits.ps1 -Mode audit -Language ru
  .\scripts\ai\grok\prepare_nine_domain_audits.ps1 -Domains docs-content,tests-system
#>
[CmdletBinding()]
param(
    [ValidateSet('audit', 'propose-patches', 'read-only', 'plan')]
    [string]$Mode = 'audit',

    [string]$Language = 'ru',

    [ValidateSet('full', 'differential')]
    [string]$AuditMode = 'full',

    # Comma-separated domain keys (see $DomainCatalog). Empty = all nine.
    [string]$Domains = '',

    [string]$RunId = '',

    [switch]$SkipRender
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $Root

$py = $null
if (Test-Path '.\.venv-win\Scripts\python.exe') {
    $py = (Resolve-Path '.\.venv-win\Scripts\python.exe').Path
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $py = (Get-Command python).Source
} else {
    throw 'Python not found (.venv-win or PATH)'
}

# domain_key -> prompt_id, report_dir, default SCOPE
$DomainCatalog = [ordered]@{
    'docs-content'       = @{
        PromptId  = 'prompt.audit.docs-content'
        ReportDir = 'reports/audit/docs-content'
        Scope     = 'README.md docs/'
        Mode      = $Mode
    }
    'tests-system'       = @{
        PromptId  = 'prompt.audit.tests-system'
        ReportDir = 'reports/audit/tests'
        Scope     = 'tests/ configs/quality/'
        Mode      = $Mode
    }
    'tech-debt'          = @{
        PromptId  = 'prompt.audit.tech-debt'
        ReportDir = 'reports/audit/tech-debt'
        Scope     = 'reports/quality/ configs/quality/ src/'
        Mode      = $Mode
    }
    'repo-tree'          = @{
        PromptId  = 'prompt.audit.repo-tree'
        ReportDir = 'reports/audit/repo-tree'
        Scope     = '.github/root-allowlist.txt scripts/ docs/00-project/governance/'
        Mode      = $Mode
    }
    'github-actions'     = @{
        PromptId  = 'prompt.audit.github-actions'
        ReportDir = 'reports/audit/gha'
        Scope     = '.github/workflows/ .github/actions/'
        Mode      = $Mode
    }
    'agents-runtime'     = @{
        PromptId  = 'prompt.audit.agents-runtime'
        ReportDir = 'reports/audit/agents'
        Scope     = 'AGENTS.md .codex/ .junie/ .devin/ docs/00-project/ai/'
        Mode      = $Mode
    }
    'diagrams'           = @{
        PromptId  = 'prompt.audit.diagrams'
        ReportDir = 'reports/audit/diagrams'
        Scope     = 'docs/02-architecture/diagrams/ scripts/diagrams/'
        Mode      = $Mode
    }
    'docs-pipeline'      = @{
        PromptId  = 'prompt.audit.docs-pipeline'
        ReportDir = 'reports/audit/docs-pipeline'
        Scope     = 'scripts/docs/ mkdocs.yml docs/'
        Mode      = $Mode
    }
    'architecture-review' = @{
        PromptId  = 'prompt.architecture.review'
        ReportDir = 'reports/audit/architecture'
        Scope     = 'src/bioetl/ docs/02-architecture/'
        Mode      = if ($Mode -eq 'audit') { 'read-only' } else { $Mode }
    }
}

$selected = @()
if ([string]::IsNullOrWhiteSpace($Domains)) {
    $selected = @($DomainCatalog.Keys)
} else {
    foreach ($d in ($Domains -split '[,;\s]+' | Where-Object { $_ })) {
        $key = $d.Trim().ToLowerInvariant()
        # aliases
        if ($key -eq 'docs' -or $key -eq 'audit.docs') { $key = 'docs-content' }
        if ($key -eq 'tests' -or $key -eq 'audit.tests') { $key = 'tests-system' }
        if ($key -eq 'gha' -or $key -eq 'audit.github-actions' -or $key -eq '.audit.github-actions') { $key = 'github-actions' }
        if ($key -eq 'agents' -or $key -eq 'audit.agents-runtime') { $key = 'agents-runtime' }
        if ($key -eq 'architecture' -or $key -eq 'architecture.review' -or $key -eq '.architecture.review') {
            $key = 'architecture-review'
        }
        if ($key -eq 'audit.tech-debt') { $key = 'tech-debt' }
        if ($key -eq 'audit.repo-tree') { $key = 'repo-tree' }
        if ($key -eq 'audit.diagrams') { $key = 'diagrams' }
        if ($key -eq 'audit.docs-pipeline') { $key = 'docs-pipeline' }
        if (-not $DomainCatalog.Contains($key)) {
            throw "Unknown domain '$d'. Known: $($DomainCatalog.Keys -join ', ')"
        }
        $selected += $key
    }
}

$sha = (git rev-parse --short HEAD 2>$null)
if (-not $sha) { $sha = 'unknown' }
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $utc = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $RunId = "$utc-$sha-nine-domain"
}

$runRoot = Join-Path $Root "reports\audit-runs\$RunId"
$promptDir = Join-Path $runRoot 'prompts'
New-Item -ItemType Directory -Force -Path $promptDir | Out-Null
foreach ($key in $selected) {
    $dir = Join-Path $Root $DomainCatalog[$key].ReportDir
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$manifest = [ordered]@{
    schema_version = 'bioetl-nine-domain-audit-prep-v1'
    run_id         = $RunId
    baseline_sha   = $sha
    mode           = $Mode
    language       = $Language
    audit_mode     = $AuditMode
    prepared_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    domains        = @()
    workflow       = @{
        rhai_tracked = 'scripts/ai/grok/workflows/nine-domain-audit.rhai'
        rhai_local   = '.grok/workflows/nine-domain-audit.rhai'
        invoke       = '/workflow nine-domain-audit'
    }
    guards         = @{
        ALLOW_ISSUE_WRITE = $false
        ALLOW_PUSH        = $false
        ALLOW_MERGE       = $false
        debt_budget_raise = $false
    }
}

Write-Host "=== Nine-domain audit prep ==="
Write-Host "run_id=$RunId"
Write-Host "domains=$($selected -join ', ')"

$prevPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($prevPythonPath) { "$Root;$prevPythonPath" } else { $Root }
try {
    foreach ($key in $selected) {
        $meta = $DomainCatalog[$key]
        $outFile = Join-Path $promptDir "$key.md"
        $entry = [ordered]@{
            domain_id   = $key
            prompt_id   = $meta.PromptId
            report_dir  = $meta.ReportDir
            scope       = $meta.Scope
            mode        = $meta.Mode
            prompt_file = "prompts/$key.md"
            status      = 'pending'
        }

        if (-not $SkipRender) {
            Write-Host "render $($meta.PromptId) -> $outFile"
            $args = @(
                '-m', 'scripts.ai.prompts', 'render', $meta.PromptId,
                '--param', "SCOPE=$($meta.Scope)",
                '--param', "MODE=$($meta.Mode)",
                '--param', "LANGUAGE=$Language",
                '--param', "AUDIT_MODE=$AuditMode",
                '--param', 'REQUIRE_GH_TRACKING=false'
            )
            & $py @args | Set-Content -Path $outFile -Encoding utf8
            if ($LASTEXITCODE -ne 0) {
                $entry.status = 'render_failed'
                Write-Warning "render failed for $key exit=$LASTEXITCODE"
            } else {
                $entry.status = 'rendered'
                $entry.bytes = (Get-Item $outFile).Length
            }
        } else {
            $entry.status = 'skipped_render'
        }
        $manifest.domains += $entry
    }
} finally {
    if ($null -eq $prevPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $prevPythonPath
    }
}

$manifestPath = Join-Path $runRoot 'manifest.json'
($manifest | ConvertTo-Json -Depth 8) | Set-Content -Path $manifestPath -Encoding utf8

$indexMd = @"
# Nine-domain audit run ``$RunId``

Prepared: $($manifest.prepared_at_utc)
Baseline: ``$sha``
Mode: ``$Mode`` / Language: ``$Language``

## Domains

| Domain | Prompt | Report dir | Status |
| --- | --- | --- | --- |
"@
foreach ($d in $manifest.domains) {
    $indexMd += "| ``$($d.domain_id)`` | ``$($d.prompt_id)`` | ``$($d.report_dir)`` | $($d.status) |`n"
}
$indexMd += @"

## How to run

### A) Paste cards (manual / multi-agent)

Open each file under ``prompts/`` and paste into a read-only agent session.
Write ``report.md`` + ``findings.json`` under the domain report dir.

### B) Grok workflow (parallel)

``````text
# After copying Rhai to machine-local .grok/workflows (if not already):
#   copy scripts\ai\grok\workflows\nine-domain-audit.rhai .grok\workflows\

/workflow nine-domain-audit
# or with args:
# domains=docs-content,tests-system language=ru mode=audit
``````

### C) Orchestrator (issues/PR loop)

Use ``prompt.audit.orchestrator`` with ``ALLOW_ISSUE_WRITE`` only when approved.
Artifacts: ``reports/audit-runs/<run_id>/``.

## Guards

- No debt-budget increases
- No ``.env`` edits without explicit approval
- No force-push / reset --hard
- Default: no GitHub mutation
"@
Set-Content -Path (Join-Path $runRoot 'README.md') -Value $indexMd -Encoding utf8

Write-Host ""
Write-Host "Prepared: $runRoot"
Write-Host "  manifest: $manifestPath"
Write-Host "  prompts:  $promptDir"
Write-Host "Next: open README.md in that folder, or /workflow nine-domain-audit"
