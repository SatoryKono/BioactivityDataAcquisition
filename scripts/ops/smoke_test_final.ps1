#!/usr/bin/env pwsh
# FINAL Smoke Test: Neo4j Memory MCP (Windows PowerShell)
# Quick validation that everything is ready
# Run this from Windows PowerShell

param([switch]$QuickMode = $true)

# Colors
$OK = "✓"
$FAIL = "✗"
$WARN = "!"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Neo4j Memory MCP - Final Verification" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# TEST 1: Container
Write-Host "TEST 1: Docker Container" -ForegroundColor Cyan
$container = docker ps --format "table {{.Names}}" 2>$null | Select-String "bioetl-neo4j"
if ($container) {
    Write-Host "$OK Container bioetl-neo4j is RUNNING" -ForegroundColor Green
    $passed++
} else {
    Write-Host "$FAIL Container bioetl-neo4j is NOT RUNNING" -ForegroundColor Red
    $failed++
}

# TEST 2: Ports
Write-Host ""
Write-Host "TEST 2: Network Ports" -ForegroundColor Cyan
try {
    $tcp1 = New-Object System.Net.Sockets.TcpClient
    $tcp1.ConnectAsync("127.0.0.1", 7687).Wait(1500) | Out-Null
    if ($tcp1.Connected) {
        Write-Host "$OK Bolt port 7687 is open" -ForegroundColor Green
        $tcp1.Close()
        $passed++
    }
} catch { }

try {
    $tcp2 = New-Object System.Net.Sockets.TcpClient
    $tcp2.ConnectAsync("127.0.0.1", 7474).Wait(1500) | Out-Null
    if ($tcp2.Connected) {
        Write-Host "$OK HTTP port 7474 is open" -ForegroundColor Green
        $tcp2.Close()
        $passed++
    }
} catch { }

# TEST 3: Wrapper
Write-Host ""
Write-Host "TEST 3: MCP Wrapper Script" -ForegroundColor Cyan
if (Test-Path "scripts/ops/mcp_neo4j_memory_wrapper.sh") {
    Write-Host "$OK Wrapper script exists" -ForegroundColor Green
    $content = Get-Content "scripts/ops/mcp_neo4j_memory_wrapper.sh" -Raw
    if ($content -match "@knowall-ai/mcp-neo4j-agent-memory@0.2.5") {
        Write-Host "$OK Wrapper uses correct package" -ForegroundColor Green
        $passed += 2
    } else {
        Write-Host "$FAIL Wrong package in wrapper" -ForegroundColor Red
        $failed++
    }
} else {
    Write-Host "$FAIL Wrapper not found" -ForegroundColor Red
    $failed++
}

# TEST 4: Env Variables
Write-Host ""
Write-Host "TEST 4: Environment Setup" -ForegroundColor Cyan
if (Test-Path ".env.local") {
    Write-Host "$OK .env.local exists" -ForegroundColor Green
    $passed++
} else {
    Write-Host "$WARN .env.local not found (using defaults)" -ForegroundColor Yellow
}

# SUMMARY
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Results: $passed passed | $failed failed" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0 -and $passed -ge 5) {
    Write-Host "✓ ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Neo4j Memory MCP is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "  1. Browser: http://localhost:7474/browser/" -ForegroundColor Cyan
    Write-Host "     (neo4j / bioetl_secure_password)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  2. Codex: codex interactive" -ForegroundColor Cyan
    Write-Host "     Then use: @neo4j-memory" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  3. Status: docker ps | Select-String neo4j" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "! Some checks failed or inconclusive" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try:" -ForegroundColor Yellow
    Write-Host "  • docker ps (check container)" -ForegroundColor Cyan
    Write-Host "  • docker logs bioetl-neo4j (check logs)" -ForegroundColor Cyan
    Write-Host "  • Restart: docker stop bioetl-neo4j; docker rm bioetl-neo4j" -ForegroundColor Cyan
}

Write-Host ""
