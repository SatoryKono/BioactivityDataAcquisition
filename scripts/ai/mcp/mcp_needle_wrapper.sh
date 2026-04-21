#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

for managed_node_prefix in \
  "${REPO_ROOT}/.cache/tools/gemini-cli/npm-global" \
  "${REPO_ROOT}/.cache/tools/codex-cli/npm-global"; do
  if [[ -x "${managed_node_prefix}/bin/node" ]]; then
    export PATH="${managed_node_prefix}/bin:${PATH}"
    break
  fi
done

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

if [[ -z "${NEEDLE_API_KEY:-}" ]]; then
  printf "NEEDLE_API_KEY is not set; Needle MCP cannot authenticate.\n" >&2
  exit 1
fi

exec npx -y mcp-remote https://mcp.needle-ai.com/mcp --silent --header "Authorization:Bearer ${NEEDLE_API_KEY}"
