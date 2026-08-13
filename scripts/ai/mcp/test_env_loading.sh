#!/usr/bin/env bash
# Quick redacted test of MCP-local repo environment loading.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. || exit 1

source scripts/ai/mcp/support/load_repo_env.sh
load_repo_env_if_present

echo "=== Environment Variables Loaded ==="
for name in BRAVE_API_KEY REF_TOOL_API_KEY NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD NEO4J_DATABASE NEO4J_AUTH; do
    if [[ -n "${!name:-}" ]]; then
        echo "${name}=SET"
    else
        echo "${name}=NOT SET"
    fi
done
echo ""

status=0
if [[ "${NEO4J_URI:-}" == "bolt://host.docker.internal:7687" ]]; then
    echo "✓ NEO4J_URI is correct"
else
    echo "✗ NEO4J_URI is incorrect or not set"
    status=1
fi

if [[ "${NEO4J_USERNAME:-}" == "neo4j" ]]; then
    echo "✓ NEO4J_USERNAME is correct"
else
    echo "✗ NEO4J_USERNAME is incorrect"
    status=1
fi

if [[ "${NEO4J_PASSWORD:-}" == *_secure_password ]]; then
    echo "✓ NEO4J_PASSWORD is correct"
else
    echo "✗ NEO4J_PASSWORD is incorrect"
    status=1
fi

if [[ "${NEO4J_DATABASE:-}" == "neo4j" ]]; then
    echo "✓ NEO4J_DATABASE is correct"
else
    echo "✗ NEO4J_DATABASE is incorrect"
    status=1
fi

exit "${status}"
