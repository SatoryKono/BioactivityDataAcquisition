#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"

export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"

if [[ -z "${NEO4J_USERNAME:-}" ]]; then
  export NEO4J_USERNAME="${NEO4J_AUTH_USERNAME:-}"
fi
if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
  export NEO4J_PASSWORD="${NEO4J_AUTH_PASSWORD:-}"
fi
if [[ -z "${NEO4J_USERNAME:-}" || -z "${NEO4J_PASSWORD:-}" ]]; then
  printf 'error: NEO4J_USERNAME and NEO4J_PASSWORD are required for Neo4j Cypher MCP\n' >&2
  exit 1
fi

export NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"
export NEO4J_URL="${NEO4J_URL:-${NEO4J_URI}}"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

mcp_validate_neo4j_credentials "Neo4j Cypher MCP"
mcp_exit_if_validate_only "neo4j-cypher"

# Node-based package (bun-based @daanrongen/neo4j-mcp fails on Windows without bun).
# Pinned to 0.2.0 for reproducibility
exec npx -y "@alanse/mcp-neo4j-server@0.2.0" "$@"
