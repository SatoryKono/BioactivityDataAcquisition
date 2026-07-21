#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

# GitHub Actions MCP configuration
# Check if local installation exists
LOCAL_GITHUB_ACTIONS_MCP="${HOME}/github-actions-mcp/dist/index.js"

if [[ -f "${LOCAL_GITHUB_ACTIONS_MCP}" ]]; then
    exec node "${LOCAL_GITHUB_ACTIONS_MCP}" --stdio
else
    # Fallback to npx if local installation not found
    exec npx -y @modelcontextprotocol/server-github-actions --stdio
fi
