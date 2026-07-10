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
source "${REPO_ROOT}/scripts/ai/mcp/support/token_validation.sh"

parse_neo4j_auth() {
    local auth_value="${1:-}"
    if [[ -z "${auth_value}" || "${auth_value}" != */* ]]; then
        return 1
    fi
    printf '%s\n' "${auth_value%%/*}" "${auth_value#*/}"
}

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USERNAME="${NEO4J_USERNAME:-${NEO4J_AUTH_USERNAME:-}}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${NEO4J_AUTH_PASSWORD:-}}"

if [[ -z "${NEO4J_USERNAME}" || -z "${NEO4J_PASSWORD}" ]] && mapfile -t auth_parts < <(parse_neo4j_auth "${NEO4J_AUTH:-}"); then
    NEO4J_USERNAME="${NEO4J_USERNAME:-${auth_parts[0]}}"
    NEO4J_PASSWORD="${NEO4J_PASSWORD:-${auth_parts[1]}}"
fi

export NEO4J_URI
export NEO4J_URL="${NEO4J_URL:-${NEO4J_URI}}"
export NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-bioetl_secure_password}"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"
mcp_validate_neo4j_credentials "Neo4j Cypher MCP"
mcp_exit_if_validate_only "neo4j-cypher"

for managed_node_prefix in \
    "${REPO_ROOT}/.cache/tools/gemini-cli/npm-global" \
    "${REPO_ROOT}/.cache/tools/codex-cli/npm-global"; do
    if [[ -x "${managed_node_prefix}/bin/node" ]]; then
        export PATH="${managed_node_prefix}/bin:${PATH}"
        break
    fi
done

exec npx -y @daanrongen/neo4j-mcp@1.1.4 "$@"
