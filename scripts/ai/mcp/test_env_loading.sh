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
if [[ "${NEO4J_URI:-}" =~ ^(bolt|neo4j)(\+s|\+ssc)?://[^[:space:]]+$ ]]; then
    echo "✓ NEO4J_URI uses a supported Neo4j scheme"
else
    echo "✗ NEO4J_URI is missing or does not use a supported Neo4j scheme"
    status=1
fi

if [[ "${NEO4J_USERNAME:-}" == "neo4j" ]]; then
    echo "✓ NEO4J_USERNAME is correct"
else
    echo "✗ NEO4J_USERNAME is incorrect"
    status=1
fi

if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
    echo "✗ NEO4J_PASSWORD is not set"
    status=1
elif [[ "${NEO4J_PASSWORD}" == *_secure_password ]]; then
    echo "✗ NEO4J_PASSWORD matches a legacy placeholder pattern"
    status=1
else
    echo "✓ NEO4J_PASSWORD is set and does not match the legacy placeholder"
fi

if [[ "${NEO4J_DATABASE:-}" == "neo4j" ]]; then
    echo "✓ NEO4J_DATABASE is correct"
else
    echo "✗ NEO4J_DATABASE is incorrect"
    status=1
fi

exit "${status}"
