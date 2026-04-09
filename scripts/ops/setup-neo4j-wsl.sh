#!/usr/bin/env bash
# Neo4j Setup and Test Script for WSL
# Note: Run this in WSL terminal, not PowerShell

set -euo pipefail

echo "=== Neo4j Backend Setup & Test (WSL) ==="
echo ""

# Configuration
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="bioetl_secure_password"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NEO4J_HOST="host.docker.internal"

# Step 1: Use docker.exe (Windows Docker Desktop daemon)
echo "Step 1: Verifying Docker connectivity via docker.exe..."
if ! command -v docker.exe &> /dev/null; then
    echo "⚠️  docker.exe not found. Ensure Docker Desktop is installed and running."
    exit 1
fi
echo "✓ docker.exe found and accessible"

# Step 2: Clean up old container
echo "Step 2: Cleaning up old containers..."
docker.exe rm -f bioetl-neo4j 2>/dev/null || true
sleep 2

# Step 3: Start Neo4j with optimized settings (via docker.exe)
echo "Step 3: Starting Neo4j 5.13-community..."
docker.exe run -d \
  --name bioetl-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e "NEO4J_AUTH=${NEO4J_USERNAME}/${NEO4J_PASSWORD}" \
  -e "NEO4J_ACCEPT_LICENSE_AGREEMENT=yes" \
  -e "NEO4J_server_memory_heap_initial__size=256m" \
  -e "NEO4J_server_memory_heap_max__size=512m" \
  -e "NEO4J_server_memory_pagecache_size=128m" \
  neo4j:5.13-community

echo "✓ Container started. Waiting 60 seconds for startup..."
sleep 60

# Step 4: Check HTTP connectivity via host.docker.internal
echo "Step 4: Testing HTTP connectivity (port 7474 via host.docker.internal)..."
if curl -s -f http://host.docker.internal:7474/ > /dev/null; then
    echo "✅ HTTP port 7474 responding on host.docker.internal"
else
    echo "⚠️  HTTP not responding yet. Waiting 15 more seconds..."
    sleep 15
fi

# Step 5: Run connection test with actual test script
echo "Step 5: Testing Bolt driver connectivity..."
if command -v node &> /dev/null; then
    driver_ready=1
    if [[ ! -f "${REPO_ROOT}/node_modules/neo4j-driver/package.json" ]]; then
        driver_ready=0
    fi
    if [[ ! -f "${REPO_ROOT}/node_modules/rxjs/dist/cjs/index.js" ]]; then
        driver_ready=0
    fi
    if [[ "${driver_ready}" -eq 0 ]]; then
        echo "→ Repairing local Node dependencies for neo4j-driver..."
        rm -rf \
          "${REPO_ROOT}/node_modules/neo4j-driver" \
          "${REPO_ROOT}/node_modules/neo4j-driver-bolt-connection" \
          "${REPO_ROOT}/node_modules/neo4j-driver-core" \
          "${REPO_ROOT}/node_modules/rxjs" \
          "${REPO_ROOT}/node_modules/tslib"
        (cd "${REPO_ROOT}" && npm install --no-save neo4j-driver rxjs tslib)
    fi
    # Use actual test script from repo root
    if [ -f "${REPO_ROOT}/test_neo4j_connection.js" ]; then
        (cd "${REPO_ROOT}" && NEO4J_URI="bolt://${NEO4J_HOST}:7687" node test_neo4j_connection.js)
    else
        echo "❌ Test script not found at ${REPO_ROOT}/test_neo4j_connection.js"
        exit 1
    fi
else
    echo "⚠️  Node.js not found. Install with: apt-get install nodejs npm"
    exit 1
fi

# Step 6: Check container logs
echo ""
echo "Step 6: Container status (last 20 lines)..."
docker.exe logs bioetl-neo4j 2>&1 | tail -20

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Verify connection test passed above"
echo "2. Seed test/docs memory from repo root:"
echo "   node seed_test_docs_memory.js"
echo "3. Verify seeded data:"
echo "   node query_test_docs_memory.js"
echo "4. Use in Codex when backend is stable: @neo4j-memory"
