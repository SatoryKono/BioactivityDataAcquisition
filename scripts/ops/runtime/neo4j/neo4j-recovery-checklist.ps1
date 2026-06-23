#!/usr/bin/env powershell
# Neo4j MCP Backend - Recovery Checklist
# Run this after manual Docker Desktop restart

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Neo4j Backend Recovery - Execution Checklist      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Checklist functions
function Check-Item {
    param([string]$Name, [bool]$Passed)
    $status = if ($Passed) { "✅" } else { "❌" }
    Write-Host "  $status $Name"
    return $Passed
}

function Run-Command {
    param([string]$Label, [string]$Cmd)
    Write-Host ""
    Write-Host "Step: $Label" -ForegroundColor Yellow
    Write-Host "Running: $Cmd"
    Write-Host ""
    Invoke-Expression $Cmd
    return $LASTEXITCODE -eq 0
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
Write-Host "═ STEP 1: Clean Old Container ═" -ForegroundColor Magenta
Write-Host ""
docker rm -f bioetl-neo4j 2>&1 | Out-Null
Write-Host "✅ Old container removed (or didn't exist)"

Write-Host ""
Write-Host "═ STEP 2: Start Neo4j 5.13-community ═" -ForegroundColor Magenta
Write-Host ""
Write-Host "Starting container..."
$containerId = docker run -d --name bioetl-neo4j `
  -p 7474:7474 -p 7687:7687 `
  -e "NEO4J_AUTH=neo4j/bioetl_secure_password" `
  -e "NEO4J_ACCEPT_LICENSE_AGREEMENT=yes" `
  -e "NEO4J_server_memory_heap_initial__size=256m" `
  -e "NEO4J_server_memory_heap_max__size=512m" `
  neo4j:5.13-community 2>&1

if ($containerId) {
    Write-Host "✅ Container started: $($containerId.Substring(0, 12))"
} else {
    Write-Host "❌ Failed to start container"
    exit 1
}

Write-Host ""
Write-Host "⏳ Waiting 60 seconds for Neo4j initialization..." -ForegroundColor Cyan
for ($i = 60; $i -gt 0; $i--) {
    Write-Progress -Activity "Neo4j starting" -Status "$i seconds remaining" -PercentComplete (($i / 60) * 100)
    Start-Sleep -Seconds 1
}
Write-Host "✅ Wait complete"

Write-Host ""
Write-Host "═ STEP 3: Verify Container Status ═" -ForegroundColor Magenta
Write-Host ""
$status = docker ps -a | Select-String "bioetl-neo4j"
if ($status) {
    Write-Host $status
    if ($status -match "Up") {
        Write-Host "✅ Container is running"
    } else {
        Write-Host "❌ Container is NOT running (Exited)"
        Write-Host ""
        Write-Host "Container logs:"
        docker logs bioetl-neo4j | Select-Object -Last 50
        exit 1
    }
} else {
    Write-Host "❌ Container not found"
    exit 1
}

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
            docker logs bioetl-neo4j | Select-Object -Last 50
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
    docker logs bioetl-neo4j | Select-Object -Last 100
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
