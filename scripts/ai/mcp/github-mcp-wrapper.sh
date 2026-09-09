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
# shellcheck source=./support/github_mcp_server.sh
source "${SCRIPT_DIR}/support/github_mcp_server.sh"

bioetl_github_mcp_resolve_token
mcp_validate_required_token \
  "GITHUB_PERSONAL_ACCESS_TOKEN" \
  20 \
  "GitHub MCP" \
  "ghp_" "github_pat_" "gho_" "ghu_" "ghs_" "ghr_"
bioetl_github_mcp_apply_policy_env
mcp_exit_if_validate_only "github"

GITHUB_MCP_BIN="$(bioetl_github_mcp_resolve_bin)"
stdio_args=(stdio --toolsets "${GITHUB_TOOLSETS}")
if [[ -n "${GITHUB_EXCLUDE_TOOLS:-}" ]]; then
  stdio_args+=(--exclude-tools "${GITHUB_EXCLUDE_TOOLS}")
fi
case "${GITHUB_LOCKDOWN_MODE:-true}" in
  0|false|FALSE|False|no|NO|off|OFF) ;;
  *) stdio_args+=(--lockdown-mode) ;;
esac

exec "${GITHUB_MCP_BIN}" "${stdio_args[@]}"
