#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

# Check if uvx is available, fallback to python3 -m uv
if command -v uvx &> /dev/null; then
    UV_CMD="uvx"
elif command -v python3 &> /dev/null; then
    UV_CMD="python3 -m uv"
else
    UV_CMD=""
fi

UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export UV_CACHE_DIR UV_TOOL_DIR
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

# Code analyzer configuration
export PROJECT_PATH="${REPO_ROOT}"

if [[ -n "${UV_CMD}" ]]; then
  if ${UV_CMD} mcp-server-analyzer --stdio "$@"; then
    exit 0
  fi
fi

exec npx -y @modelcontextprotocol/server-analyzer --stdio "$@"
