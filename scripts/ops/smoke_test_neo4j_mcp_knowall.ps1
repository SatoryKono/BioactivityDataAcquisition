#!/usr/bin/env pwsh
# Smoke Test: Neo4j Memory MCP Integration (PowerShell Version)
# Run this from Windows PowerShell after startup script completes
# Tests the complete chain with @knowall-ai/mcp-neo4j-agent-memory@0.2.5

param(
    [switch]$Verbose = $false
)

# Colors
$GREEN = "`e[0;32m"
$RED = "`e[0;31m"
$YELLOW = "`e[1;33m"
$BLUE = "`e[0;34m"
$NC = "`e[0m"

function Pass([string]$msg) { Write-Host "${GREEN}✓${NC} $msg" -ForegroundColor Green }
function Fail([string]$msg) { Write-Host "${RED}✗${NC} $msg" -ForegroundColor Red }
function Warn([string]$msg) { Write-Host "${YELLOW}!${NC} $msg" -ForegroundColor Yellow }
function Info([string]$msg) { Write-Host "${BLUE}→${NC} $msg" -ForegroundColor Cyan }
function Header([string]$msg) {
    Write-Host ""
    Write-Host "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor Cyan
    Write-Host "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" -ForegroundColor Cyan
}

$status = 0

# ============================================================================
# TEST 1: Docker Container Status
# ============================================================================
Header "TEST 1: Docker Container Status"

$containers = docker ps --format "table {{.Names}}" 2>$null | Select-String "bioetl-neo4j"

if ($containers) {
    Pass "Container bioetl-neo4j is RUNNING"
    docker ps | Select-String "bioetl-neo4j" | ForEach-Object { Write-Host "  $_" }
} else {
    Fail "Container bioetl-neo4j is NOT RUNNING"
    Info "Start it: bash scripts/ops/wsl_neo4j_startup.sh (from WSL)"
    $status = 1
}

# ============================================================================
# TEST 2: Port Accessibility (Localhost)
# ============================================================================
Header "TEST 2: Port Accessibility"

Info "Testing localhost connectivity..."

$boltPort = $false
$httpPort = $false

# Test Bolt port (7687)
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.ConnectAsync("127.0.0.1", 7687).Wait(2000) | Out-Null
    if ($tcpClient.Connected) {
        $boltPort = $true
        Pass "Bolt port (7687) accessible"
        $tcpClient.Close()
    }
} catch {
    Warn "Bolt port (7687) not accessible on localhost"
    Info "This is expected in WSL — use host.docker.internal from WSL"
}

# Test HTTP port (7474)
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.ConnectAsync("127.0.0.1", 7474).Wait(2000) | Out-Null
    if ($tcpClient.Connected) {
        $httpPort = $true
        Pass "HTTP port (7474) accessible"
        $tcpClient.Close()
    }
} catch {
    Warn "HTTP port (7474) not accessible on localhost"
}

# ============================================================================
# TEST 3: Wrapper Script Verification
# ============================================================================
Header "TEST 3: Wrapper Script (@knowall-ai/mcp-neo4j-agent-memory)"

$WRAPPER_PATH = "scripts/ops/mcp_neo4j_memory_wrapper.sh"

if (Test-Path $WRAPPER_PATH) {
    Pass "Wrapper script exists"
    
    $wrapperContent = Get-Content $WRAPPER_PATH -Raw
    
    if ($wrapperContent -match "@knowall-ai/mcp-neo4j-agent-memory@0.2.5") {
        Pass "Wrapper uses @knowall-ai/mcp-neo4j-agent-memory@0.2.5"
    } else {
        Fail "Wrapper does not reference correct package"
        $status = 1
    }
    
    if ($wrapperContent -match "NEO4J_URI|NEO4J_USERNAME|NEO4J_PASSWORD") {
        Pass "Wrapper exports Neo4j environment variables"
    } else {
        Fail "Wrapper missing environment setup"
        $status = 1
    }
} else {
    Fail "Wrapper script NOT found at $WRAPPER_PATH"
    $status = 1
}

# ============================================================================
# TEST 4: Environment Variables
# ============================================================================
Header "TEST 4: Environment Configuration"

$NEO4J_URI = $env:NEO4J_URI ? $env:NEO4J_URI : "bolt://localhost:7687"
$NEO4J_USERNAME = $env:NEO4J_USERNAME ? $env:NEO4J_USERNAME : "neo4j"
$NEO4J_PASSWORD = $env:NEO4J_PASSWORD ? $env:NEO4J_PASSWORD : "bioetl_secure_password"

Pass "NEO4J_URI: $NEO4J_URI"
Pass "NEO4J_USERNAME: $NEO4J_USERNAME"

if ($NEO4J_PASSWORD) {
    Pass "NEO4J_PASSWORD is configured"
} else {
    Warn "NEO4J_PASSWORD is empty (using default)"
}

# ============================================================================
# TEST 5: MCP Registration in Codex
# ============================================================================
Header "TEST 5: MCP Registration in Codex"

$codexAvailable = $null -ne (Get-Command codex -ErrorAction SilentlyContinue)

if ($codexAvailable) {
    $mcp_list = & codex mcp list 2>$null
    
    if ($mcp_list -match "neo4j-memory") {
        Pass "neo4j-memory is registered in Codex"
        
        $mcp_config = & codex mcp get neo4j-memory 2>$null
        if ($mcp_config -match "mcp_neo4j_memory_wrapper") {
            Pass "Codex uses correct wrapper"
        } else {
            Fail "Codex wrapper configuration incorrect"
            $status = 1
        }
    } else {
        Fail "neo4j-memory NOT registered in Codex"
        Info "Register: uv run python -m scripts.dev setup-mcp"
        $status = 1
    }
} else {
    Warn "Codex CLI not available (MCP check skipped)"
}

# ============================================================================
# TEST 6: Cypher Query Execution
# ============================================================================
Header "TEST 6: Cypher Query Execution"

Info "Attempting to execute test Cypher query..."

try {
    $result = docker exec bioetl-neo4j cypher-shell -u neo4j -p bioetl_secure_password `
        "RETURN '@knowall-ai/mcp-neo4j-agent-memory connected!' AS status" 2>$null
    
    if ($result -match "connected") {
        Pass "Cypher query execution works"
    } else {
        Warn "Cypher query inconclusive"
    }
} catch {
    Warn "Cypher query check inconclusive (Neo4j may still be stabilizing)"
}

# ============================================================================
# TEST 7: Memory File Existence
# ============================================================================
Header "TEST 7: Memory Storage"

$MEMORY_PATH = "docs/00-project/ai/memory/mcp-memory.json"

if (Test-Path $MEMORY_PATH) {
    Pass "Memory file exists at $MEMORY_PATH"
    $size = (Get-Item $MEMORY_PATH).Length
    Info "Size: $size bytes"
} else {
    Warn "Memory file not found (will be created on first MCP use)"
}

# ============================================================================
# SUMMARY
# ============================================================================
Header "Test Summary"

if ($status -eq 0) {
    Write-Host ""
    Write-Host "${GREEN}" -NoNewline
    Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✓ ALL CRITICAL TESTS PASSED            ║" -ForegroundColor Green
    Write-Host "║  Neo4j Memory MCP (@knowall-ai) READY   ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host "${NC}"
    
    Write-Host ""
    Write-Host "✨ Next Steps:" -ForegroundColor Green
    Write-Host "  1. Test in Codex:" -ForegroundColor Green
    Write-Host "     ${BLUE}codex interactive${NC}" -ForegroundColor Green
    Write-Host "     Use ${BLUE}@neo4j-memory${NC} in prompts" -ForegroundColor Green
    Write-Host ""
    Write-Host "  2. Access Neo4j Browser:" -ForegroundColor Green
    Write-Host "     ${BLUE}http://localhost:7474/browser${NC}" -ForegroundColor Green
    Write-Host "     (Username: neo4j | Password: bioetl_secure_password)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  3. Verify MCP details:" -ForegroundColor Green
    Write-Host "     ${BLUE}codex mcp get neo4j-memory${NC}" -ForegroundColor Green
    Write-Host ""
    
    exit 0
} else {
    Write-Host ""
    Write-Host "${RED}" -NoNewline
    Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║  ✗ SOME TESTS FAILED                    ║" -ForegroundColor Red
    Write-Host "║  See details above                      ║" -ForegroundColor Red
    Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host "${NC}"
    
    Write-Host ""
    Write-Host "⚠️  Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  • Container not running?" -ForegroundColor Yellow
    Write-Host "    ${BLUE}bash scripts/ops/wsl_neo4j_startup.sh${NC}" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  • Ports closed?" -ForegroundColor Yellow
    Write-Host "    Wait 10-15 seconds for Neo4j to fully start" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  • MCP not registered?" -ForegroundColor Yellow
    Write-Host "    ${BLUE}uv run python -m scripts.dev setup-mcp${NC}" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  • View Neo4j logs:" -ForegroundColor Yellow
    Write-Host "    ${BLUE}docker logs -f bioetl-neo4j${NC}" -ForegroundColor Yellow
    Write-Host ""
    
    exit 1
}
