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

# Auto-recall path configuration
export DEJA_AUTO_RECALL_PATH="${REPO_ROOT}/.codex/AGENTS.md"

mcp_exit_if_validate_only "deja"

# Published package moved off @modelcontextprotocol/server-deja-vu (404).
# Current package: @vshulcz/deja-vu (bin: deja).
exec npx -y "@vshulcz/deja-vu@0.15.0" --stdio
