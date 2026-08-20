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
source "${REPO_ROOT}/scripts/ai/mcp/support/token_validation.sh"

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"

# Preserve compatibility with local shells that still export the legacy token name.
if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_TOKEN}"
fi

mcp_validate_required_token \
  "GITHUB_PERSONAL_ACCESS_TOKEN" \
  20 \
  "GitHub MCP" \
  "ghp_" "github_pat_" "gho_" "ghu_" "ghs_" "ghr_"
mcp_exit_if_validate_only "github"

exec npx -y "@modelcontextprotocol/server-github@2025.4.8" --stdio
