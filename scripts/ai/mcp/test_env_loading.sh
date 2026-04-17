#!/usr/bin/env bash
# Quick test that the MCP-local repo env loader resolves Neo4j settings correctly.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. || exit 1

source scripts/ai/mcp/support/load_repo_env.sh
load_repo_env_if_present

echo "=== Environment Variables Loaded ==="
echo "NEO4J_URI=${NEO4J_URI:-NOT SET}"
echo "NEO4J_USERNAME=${NEO4J_USERNAME:-NOT SET}"
echo "NEO4J_PASSWORD=${NEO4J_PASSWORD:-NOT SET}"
echo "NEO4J_DATABASE=${NEO4J_DATABASE:-NOT SET}"
echo "NEO4J_AUTH=${NEO4J_AUTH:-NOT SET}"
echo ""

if [[ "${NEO4J_URI:-}" == "bolt://host.docker.internal:7687" ]]; then
    echo "✓ NEO4J_URI is correct"
else
    echo "✗ NEO4J_URI is incorrect or not set"
fi

if [[ "${NEO4J_USERNAME:-}" == "neo4j" ]]; then
    echo "✓ NEO4J_USERNAME is correct"
else
    echo "✗ NEO4J_USERNAME is incorrect"
fi

if [[ "${NEO4J_PASSWORD:-}" == "bioetl_secure_password" ]]; then
    echo "✓ NEO4J_PASSWORD is correct"
else
    echo "✗ NEO4J_PASSWORD is incorrect"
fi

if [[ "${NEO4J_DATABASE:-}" == "neo4j" ]]; then
    echo "✓ NEO4J_DATABASE is correct"
else
    echo "✗ NEO4J_DATABASE is incorrect"
fi
