#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./support/invoke_host_transport.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/support/invoke_host_transport.sh"
if run_mcp_host_route ast-grep "$@"; then
  exit 0
else
  mcp_host_status=$?
  if [[ "${mcp_host_status}" -ne 78 ]]; then exit "${mcp_host_status}"; fi
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"

if [[ "${BIOETL_MCP_VALIDATE_ONLY:-0}" == "1" ]]; then
  command -v npx >/dev/null 2>&1 || mcp_fail "npx is required for ast-grep MCP"
  mcp_exit_if_validate_only "ast-grep"
fi

mcp_prepare_npm_cache

# MCP server packages (not plain @ast-grep/cli).
if npx -y @notprolands/ast-grep-mcp@1.1.1 --stdio "$@"; then
  exit 0
fi

exec npx -y @chousyn/ast-grep-mcp@0.1.1 --stdio "$@"
