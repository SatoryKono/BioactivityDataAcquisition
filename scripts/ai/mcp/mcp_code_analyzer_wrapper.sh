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

UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export UV_CACHE_DIR UV_TOOL_DIR
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"
export PROJECT_PATH="${REPO_ROOT}"

mcp_exit_if_validate_only "code-analyzer"

# Prefer published npm MCP package (legacy mcp-server-analyzer packages are 404).
if command -v uvx >/dev/null 2>&1; then
  if uvx mcp-server-analyzer --stdio "$@"; then
    exit 0
  fi
fi

exec npx -y "@darient/code-analyzer-mcp" --stdio "$@"
