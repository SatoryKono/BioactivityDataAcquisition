#!/usr/bin/env powershell
# Neo4j MCP Backend - Recovery Checklist
# Run this after manual Docker Desktop restart

$InformationPreference = 'Continue'

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Neo4j Backend Recovery - Execution Checklist      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Checklist functions
function Test-ChecklistItem {
    param([string]$Name, [bool]$Passed)
    $status = if ($Passed) { "✅" } else { "❌" }
    Write-Information "  $status $Name" -InformationAction Continue
    return $Passed
}

function Invoke-ChecklistCommand {
    param(
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [string[]]$CommandArgs
    )
    Write-Host ""
    Write-Host "Step: $Label" -ForegroundColor Yellow
    Write-Host "Running: $($CommandArgs -join ' ')"
    Write-Host ""
    # argv-only invocation avoids Invoke-Expression (powershelldre:S8659).
    & $CommandArgs[0] @($CommandArgs | Select-Object -Skip 1)
    return $LASTEXITCODE -eq 0
}

# Backward-compatible name used by checklist steps below.
function Run-Command {
    param([string]$Label, [string]$Cmd)
    # Split on whitespace for fixed recovery commands only (no user shell metacharacters).
    $parts = @($Cmd.Trim() -split '\s+')
    return Invoke-ChecklistCommand -Label $Label -CommandArgs $parts
}

# Pre-flight checks
Write-Host "═ PRE-FLIGHT CHECKS ═" -ForegroundColor Magenta
Write-Host ""

$dockerResponds = $false
try {
    $result = docker ps 2>&1
    if ($?) {
        Write-Host "✅ Docker daemon is responsive"
        $dockerResponds = $true
    } else {
        Write-Host "❌ Docker daemon NOT responsive"
        Write-Host "   ACTION: Restart Docker Desktop manually"
        Write-Host "   - Right-click tray icon → Quit Docker Desktop"
        Write-Host "   - Wait 10 seconds"
        Write-Host "   - Relaunch from Start menu"
        Write-Host "   - Wait 60 seconds"
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host "❌ Docker daemon error: $_"
    Write-Host "   ACTION: Restart Docker Desktop"
    exit 1
}

Write-Host ""
Write-Host "═ STEP 1: Validate Compose Owner ═" -ForegroundColor Magenta
Write-Host ""
if ([string]::IsNullOrWhiteSpace($env:NEO4J_USERNAME) -or
    [string]::IsNullOrWhiteSpace($env:NEO4J_PASSWORD)) {
    Write-Host "❌ NEO4J_USERNAME and NEO4J_PASSWORD are required" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "docker-compose.neo4j.yml")) {
    Write-Host "❌ Run this checklist from the repository root" -ForegroundColor Red
    exit 1
}

docker network inspect bioetl-runtime *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ External network bioetl-runtime is missing" -ForegroundColor Red
    Write-Host "   Run scripts/ops/docker-setup.ps1 first."
    exit 1
}
Write-Host "✅ Compose owner inputs are present"

Write-Host ""
Write-Host "═ STEP 2: Start bioetl-neo4j Compose Project ═" -ForegroundColor Magenta
Write-Host ""
Write-Host "Running: docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait --wait-timeout 240"
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait --wait-timeout 240
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Compose project failed readiness" -ForegroundColor Red
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml logs --tail 50 neo4j
    exit 1
}
Write-Host "✅ Compose project is healthy"

Write-Host ""
Write-Host "═ STEP 3: Verify Container Status ═" -ForegroundColor Magenta
Write-Host ""
$status = docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml ps --status running neo4j
if ($LASTEXITCODE -ne 0 -or -not ($status -match "neo4j")) {
    Write-Host "❌ Compose-owned Neo4j service is not running"
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml logs --tail 50 neo4j
    exit 1
}
Write-Host $status
Write-Host "✅ Compose-owned container is running"

Write-Host ""
Write-Host "═ STEP 4: Test HTTP Port (7474) ═" -ForegroundColor Magenta
Write-Host ""
Write-Host "Testing: curl http://localhost:7474/"
try {
    $response = curl.exe -s -w "%{http_code}" -o $null http://localhost:7474/ 2>&1
    if ($response -match "200|302|404") {
        Write-Host "✅ HTTP port 7474 responding (HTTP $response)"
    } else {
        Write-Host "⚠️  HTTP port 7474 not responding yet"
        Write-Host "   Waiting 30 more seconds..."
        Start-Sleep -Seconds 30

        $response = curl.exe -s -w "%{http_code}" -o $null http://localhost:7474/ 2>&1
        if ($response -match "200|302|404") {
            Write-Host "✅ HTTP port now responding (HTTP $response)"
        } else {
            Write-Host "❌ HTTP port still not responding"
            Write-Host "   Container may have crashed. Check logs:"
            docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml logs --tail 50 neo4j
            exit 1
        }
    }
} catch {
    Write-Host "⚠️  curl failed: $_"
}

Write-Host ""
Write-Host "═ STEP 5: Verify MCP and Backend (7687) ═" -ForegroundColor Magenta
Write-Host ""
Write-Host "Testing: bash scripts/ai/mcp/check_neo4j_memory.sh"
Write-Host ""

if (-not (Test-Path "scripts/ai/mcp/check_neo4j_memory.sh")) {
    Write-Host "❌ scripts/ai/mcp/check_neo4j_memory.sh not found"
    exit 1
}

$driverTestPassed = $false
if (Get-Command bash -ErrorAction SilentlyContinue) {
    try {
        & bash scripts/ai/mcp/check_neo4j_memory.sh
        $driverTestPassed = $LASTEXITCODE -eq 0
    } catch {
        Write-Host "❌ Error running verification: $_"
        $driverTestPassed = $false
    }
} elseif (Get-Command codex -ErrorAction SilentlyContinue) {
    try {
        & codex mcp get neo4j-memory
        $driverTestPassed = $LASTEXITCODE -eq 0
    } catch {
        Write-Host "❌ Error checking Codex MCP registration: $_"
        $driverTestPassed = $false
    }
} else {
    Write-Host "❌ Neither bash nor codex is available for verification"
    $driverTestPassed = $false
}

if ($driverTestPassed) {
    Write-Host ""
    Write-Host "✅ MCP/backend verification PASSED"
} else {
    Write-Host ""
    Write-Host "❌ MCP/backend verification FAILED"
    Write-Host ""
    Write-Host "Detailed container logs:"
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml logs --tail 100 neo4j
    exit 1
}

Write-Host ""
Write-Host "═ STEP 6: Verify Environment ═" -ForegroundColor Magenta
Write-Host ""
if (Test-Path ".env.local") {
    Write-Host "✅ .env.local exists"
    $envContent = Get-Content .env.local | Select-String "NEO4J_URI"
    Write-Host "   $envContent"
} else {
    Write-Host "⚠️  .env.local not found (MCP may not have credentials)"
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            ✅ ALL TESTS PASSED - BACKEND READY         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Verify MCP in Codex:"
Write-Host "   codex interactive"
Write-Host "   Type: @neo4j-memory"
Write-Host ""
Write-Host "2. Run deterministic memory audit:"
Write-Host "   python -m scripts.memory sync --report-fast --report /tmp/neo4j-memory-audit.json"
Write-Host ""
Write-Host "3. Apply deterministic memory sync when ready:"
Write-Host "   python -m scripts.memory sync --apply"
Write-Host ""
Write-Host "Backend is now ready for MCP integration! 🎉"
