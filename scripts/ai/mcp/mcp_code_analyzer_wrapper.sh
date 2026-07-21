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
    echo "Error: Neither uvx nor python3 with uv module found" >&2
    exit 1
fi

UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export UV_CACHE_DIR UV_TOOL_DIR

# Code analyzer configuration
export PROJECT_PATH="${REPO_ROOT}"

exec ${UV_CMD} mcp-server-analyzer --stdio
