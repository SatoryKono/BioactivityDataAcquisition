#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
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

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USERNAME="${NEO4J_USERNAME:-${NEO4J_AUTH_USERNAME:-}}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${NEO4J_AUTH_PASSWORD:-}}"

if [[ -z "${NEO4J_USERNAME}" || -z "${NEO4J_PASSWORD}" ]]; then
    if mapfile -t auth_parts < <(parse_neo4j_auth "${NEO4J_AUTH:-}"); then
        NEO4J_USERNAME="${NEO4J_USERNAME:-${auth_parts[0]}}"
        NEO4J_PASSWORD="${NEO4J_PASSWORD:-${auth_parts[1]}}"
    fi
fi

export NEO4J_URI
export NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-bioetl_secure_password}"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"

exec npx -y @modelcontextprotocol/server-neo4j@1.0.0 "$@"
