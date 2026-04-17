#!/usr/bin/env bash
# Neo4j Memory MCP - WSL Copy-Paste Commands
# Run these commands in order on your WSL machine

# ============================================================================
# STEP 1: Start Neo4j Backend (WSL-Optimized)
# ============================================================================
echo "Starting Neo4j backend..."
bash scripts/memory/setup/wsl_startup.sh

# Expected output:
# ✓ Neo4j backend is running
# ✓ MCP wrapper is configured
# ✓ Ready for smoke test

# ============================================================================
# STEP 2: Verify Everything Works
# ============================================================================
echo ""
echo "Running verification tests..."
bash scripts/memory/mcp/check.sh

# Expected output:
# ╔═══════════════════════════════════════════╗
# ║  ✓ ALL CRITICAL TESTS PASSED            ║
# ║  Neo4j Memory MCP READY                 ║
# ╚═══════════════════════════════════════════╝

# ============================================================================
# STEP 3: Access Neo4j Browser (from WSL)
# ============================================================================
# Open in browser:
# http://host.docker.internal:7474/browser/
#
# Username: neo4j
# Password: bioetl_secure_password

# ============================================================================
# STEP 4: Use in Codex
# ============================================================================
echo ""
echo "Starting Codex interactive mode..."
codex interactive

# In Codex, use:
# @neo4j-memory to store and query knowledge in Neo4j

# ============================================================================
# USEFUL COMMANDS FOR LATER
# ============================================================================
# Check container status:
# docker ps | grep bioetl-neo4j

# View logs:
# docker logs -f bioetl-neo4j

# Check MCP status:
# codex mcp get neo4j-memory

# Verify all MCP servers:
# bash scripts/ops/check_mcp.sh

# Stop container (keeps data):
# docker stop bioetl-neo4j

# Remove container (clean up):
# docker rm bioetl-neo4j

# ============================================================================
# COMPLETE! Your Neo4j Memory MCP is ready to use
# ============================================================================
