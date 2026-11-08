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

mcp_validate_optional_token "CONTEXT7_API_KEY" 8 "Context7 MCP (optional higher rate limits)"
mcp_exit_if_validate_only "context7"
mcp_prepare_npm_cache

shared_client="${REPO_ROOT}/scripts/ops/runtime/mcp/stdio_shared_client.py"
if [[ -f "$shared_client" ]] && { [[ -n "${WSL_INTEROP:-}" ]] || grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; }; then
    exec python3 "$shared_client" context7
elif [[ -f "$shared_client" && -f "/c/Program Files/nodejs/node.exe" && -f "/d/pc-agent/tools/shared-mcp/service-owner.py" ]]; then
    exec "/c/Program Files/nodejs/node.exe" "D:/pc-agent/tools/shared-mcp/service-adapter.mjs" context7
fi

# CONTEXT7_API_KEY is inherited by the child; never expose it in process argv.
exec npx -y "@upstash/context7-mcp@3.2.4"
