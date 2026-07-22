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

# ADR analysis configuration (mcp-adr-analysis-server)
export PROJECT_PATH="${REPO_ROOT}"
export ADR_PATH="${REPO_ROOT}/docs/02-architecture/decisions"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

mcp_exit_if_validate_only "adr-analysis"

# Published package: mcp-adr-analysis-server (bin: mcp-adr-analysis-server)
exec npx -y mcp-adr-analysis-server --stdio
