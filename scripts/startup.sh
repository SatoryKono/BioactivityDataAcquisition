#!/bin/bash
# Compatibility wrapper for the legacy root startup launcher.
# Stable startup script for BioETL + MCP servers
# Usage: ./scripts/startup.sh [prod|dev]

set -e

ENV=${1:-dev}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 Starting BioETL stack (environment: $ENV)..."

# Create required networks and volumes
echo "📡 Ensuring Docker network exists..."
docker network create warp-network 2>/dev/null || true
docker network create bioetl-monitoring 2>/dev/null || true

# Check if warp-network exists and is accessible
if ! docker network inspect warp-network >/dev/null 2>&1; then
    echo "❌ Network warp-network not found"
    exit 1
fi

# Pre-pull images to avoid delays
echo "🔄 Pre-pulling images..."
docker compose -p bioetl-codex -f "$PROJECT_DIR/docker-compose.codex.yml" pull --quiet 2>/dev/null || true

# Start base infrastructure (Neo4j, etc.)
if [ "$ENV" = "prod" ]; then
    echo "🏗️  Starting production stack..."
    docker compose -p bioetl-main -f "$PROJECT_DIR/docker-compose.yml" up -d
    sleep 5
fi

# Start MCP servers
echo "🤖 Starting MCP servers..."
docker compose -p bioetl-codex -f "$PROJECT_DIR/docker-compose.codex.yml" up -d

# Wait for critical services
echo "⏳ Waiting for services to stabilize..."
sleep 3

# Health check
echo "✅ Checking service status..."
CONTAINERS=(
    "bioetl-mcp-memory"
    "bioetl-mcp-filesystem"
    "bioetl-mcp-github"
    "bioetl-mcp-fetch"
    "bioetl-codex-config"
)

FAILED=0
for container in "${CONTAINERS[@]}"; do
    if docker ps --filter "name=$container" --filter "status=running" --quiet >/dev/null; then
        echo "  ✓ $container"
    else
        echo "  ✗ $container (check with: docker logs $container)"
        ((FAILED++))
    fi
done

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "✨ All MCP servers are running!"
    echo ""
    echo "📊 Dashboard: http://localhost:9100"
    echo "💾 Memory: bioetl-mcp-memory"
    echo "📁 Filesystem: bioetl-mcp-filesystem"
    echo "🐙 GitHub: bioetl-mcp-github"
    echo ""
    echo "View logs with: docker compose -p bioetl-codex -f docker-compose.codex.yml logs -f"
else
    echo ""
    echo "⚠️  $FAILED service(s) failed to start"
    exit 1
fi
