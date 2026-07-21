#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export UV_CACHE_DIR UV_TOOL_DIR
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

# Mutmut MCP configuration
export MUTMUT_PROJECT_PATH="${REPO_ROOT}"

if command -v uvx >/dev/null 2>&1; then
  if uvx --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio "$@"; then
    exit 0
  fi
elif command -v python3 >/dev/null 2>&1; then
  if python3 -m uv --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio "$@"; then
    exit 0
  fi
else
  echo "Error: Neither uvx nor python3 with uv module found" >&2
  exit 1
fi

exec npx -y "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio "$@"
