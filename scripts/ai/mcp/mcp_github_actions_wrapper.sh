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

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

# Prefer a local checkout when present; otherwise use published npm package.
LOCAL_GITHUB_ACTIONS_MCP="${HOME}/github-actions-mcp/dist/index.js"
LOCAL_GITHUB_ACTIONS_MAIN="${HOME}/github-actions-mcp/dist/main.js"

mcp_exit_if_validate_only "github-actions"

if [[ -f "${LOCAL_GITHUB_ACTIONS_MCP}" ]]; then
    exec node "${LOCAL_GITHUB_ACTIONS_MCP}" --stdio
elif [[ -f "${LOCAL_GITHUB_ACTIONS_MAIN}" ]]; then
    exec node "${LOCAL_GITHUB_ACTIONS_MAIN}" --stdio
fi

# Published package: github-actions-mcp (bin: github-actions-mcp)
# (The old @modelcontextprotocol/server-github-actions package is 404.)
exec npx -y "github-actions-mcp@1.0.1" --stdio
