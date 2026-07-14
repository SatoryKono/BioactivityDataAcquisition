#!/bin/bash
# Compatibility wrapper for the legacy root shutdown launcher.
# Graceful shutdown script for BioETL + MCP servers

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🛑 Stopping BioETL services..."

# Stop MCP servers
echo "Stopping MCP servers..."
docker compose -p bioetl-codex -f "$PROJECT_DIR/docker-compose.codex.yml" down --remove-orphans 2>/dev/null || true

# Optional: Stop base infrastructure (comment out to keep running)
echo "Stopping base infrastructure..."
docker compose -p bioetl-main -f "$PROJECT_DIR/docker-compose.yml" down --remove-orphans 2>/dev/null || true

echo "✓ Services stopped gracefully"
echo ""
echo "To remove all volumes (data cleanup): docker system prune -a"
