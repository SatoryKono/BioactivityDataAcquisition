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

export PROJECT_PATH="${REPO_ROOT}"
export ADR_PATH="${ADR_PATH:-${REPO_ROOT}/docs/02-architecture/decisions}"
# Default to prompt-only so the server works without OPENROUTER_API_KEY.
export EXECUTION_MODE="${EXECUTION_MODE:-prompt-only}"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${TMPDIR:-/tmp}/bioetl-npm-cache}"
# tree-sitter native modules often fail outside a full node-gyp toolchain;
# the server supports reduced mode without them. npm's documented config key is
# lowercase; pass it only as a child process env (shelldre:S7684 / no shell export).
export NPM_CONFIG_IGNORE_SCRIPTS="${NPM_CONFIG_IGNORE_SCRIPTS:-true}"

mcp_exit_if_validate_only "adr-analysis"

# Package defaults to stdio MCP transport. Do not pass a bare "--stdio" flag.
exec env \
  "NPM_CONFIG_IGNORE_SCRIPTS=${NPM_CONFIG_IGNORE_SCRIPTS}" \
  "npm_config_ignore_scripts=${NPM_CONFIG_IGNORE_SCRIPTS}" \
  npx -y mcp-adr-analysis-server@2.6.14
