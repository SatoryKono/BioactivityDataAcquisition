#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"

if [[ -z "${NEEDLE_API_KEY:-}" ]]; then
  printf "NEEDLE_API_KEY is not set; Needle MCP cannot authenticate.\n" >&2
  exit 1
fi

exec npx -y mcp-remote https://mcp.needle-ai.com/mcp --header "Authorization:Bearer ${NEEDLE_API_KEY}"
