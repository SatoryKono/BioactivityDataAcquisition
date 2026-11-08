#!/usr/bin/env bash

set -euo pipefail

# Optional host route is resolved before env/cache/Docker side effects.
mcp_host_marker="${PC_AGENT_MCP_ROUTES_FILE:-${HOME}/.config/pc-agent/mcp-routes.json}"
if [[ -n "${PC_AGENT_MCP_ROUTES_FILE:-}" || -e "${mcp_host_marker}" || -L "${mcp_host_marker}" ]]; then
  mcp_host_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  mcp_host_root="$(cd -- "${mcp_host_dir}/../../.." && pwd)"
  if command -v cygpath >/dev/null 2>&1; then
    mcp_host_root="$(cygpath -w "${mcp_host_root}")"
  fi
  if node "${mcp_host_dir}/support/host_transport.mjs" --root "${mcp_host_root}" --server context7 -- "$@"; then
    exit 0
  else
    mcp_host_status=$?
    if [[ "${mcp_host_status}" -ne 78 ]]; then exit "${mcp_host_status}"; fi
  fi
fi
unset mcp_host_marker

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

mcp_validate_optional_token "CONTEXT7_API_KEY" 8 "Context7 MCP (optional higher rate limits)"
mcp_exit_if_validate_only "context7"
mcp_prepare_npm_cache

# CONTEXT7_API_KEY is inherited by the child; never expose it in process argv.
exec npx -y "@upstash/context7-mcp@3.2.4"
