#!/usr/bin/env bash

# Neo4j Memory MCP Server Wrapper
# Handles connection to Neo4j and memory management via MCP

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

parse_neo4j_auth() {
    local auth_value="${1:-}"
    if [[ -z "${auth_value}" || "${auth_value}" != */* ]]; then
        return 1
    fi
    printf '%s\n' "${auth_value%%/*}" "${auth_value#*/}"
}

# Get Neo4j connection details from environment.
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USERNAME="${NEO4J_USERNAME:-${NEO4J_AUTH_USERNAME:-}}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${NEO4J_AUTH_PASSWORD:-}}"

if [[ -z "${NEO4J_USERNAME}" || -z "${NEO4J_PASSWORD}" ]]; then
    if mapfile -t auth_parts < <(parse_neo4j_auth "${NEO4J_AUTH:-}"); then
        NEO4J_USERNAME="${NEO4J_USERNAME:-${auth_parts[0]}}"
        NEO4J_PASSWORD="${NEO4J_PASSWORD:-${auth_parts[1]}}"
    fi
fi

NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-bioetl_secure_password}"
NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

# Set environment for MCP server
export NEO4J_URI
export NEO4J_USERNAME
export NEO4J_PASSWORD
export NEO4J_DATABASE
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || true)}"
if [[ -z "${PYTHON_BIN}" ]]; then
    printf '%s\n' "Python interpreter not found for neo4j-memory MCP adapter" >&2
    exit 1
fi

# The upstream server still speaks line-delimited JSON over stdio. Bridge it to the
# framed MCP transport expected by Codex and other repo tooling.
exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/ai/mcp/neo4j_memory_mcp_adapter.py" -- \
    npx -y @knowall-ai/mcp-neo4j-agent-memory@0.2.5 "$@"
