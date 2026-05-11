#!/bin/bash
# Start Codex MCP servers under WSL2

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🚀 Starting Codex MCP servers under WSL2..."
echo "Project directory: $PROJECT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Loaded .env file"
else
    echo "⚠ .env file not found, using defaults"
fi

# Ensure warp-network exists
if ! docker network inspect warp-network > /dev/null 2>&1; then
    echo "Creating warp-network..."
    docker network create warp-network
fi

# Start MCP services
echo "Starting MCP servers..."
docker compose -f docker-compose.codex.yml up -d

# Wait for services to stabilize
echo "Waiting for services to be ready..."
sleep 8

# Verify services
echo ""
echo "Service Status:"
docker ps -f name=bioetl-mcp --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "================================"
echo "✓ Codex MCP servers ready!"
echo "================================"
echo ""
echo "MCP Servers:"
echo "  • Memory:      bioetl-mcp-memory"
echo "  • Filesystem:  bioetl-mcp-filesystem"
echo "  • GitHub:      bioetl-mcp-github"
echo "  • Docker:      bioetl-mcp-docker"
echo ""
echo "Next: Open Anthropic Codex and add MCP servers via settings.json"
echo ""
echo "Useful commands:"
echo "  View logs:     docker compose -f docker-compose.codex.yml logs -f"
echo "  Stop servers:  docker compose -f docker-compose.codex.yml down"
echo "  Restart:       docker compose -f docker-compose.codex.yml restart"
echo ""
