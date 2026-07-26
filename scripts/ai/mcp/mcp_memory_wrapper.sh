#!/usr/bin/env bash
# MCP memory server pinned to one repository-owned knowledge graph file.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
source "${SCRIPT_DIR}/support/load_repo_env.sh"
export BIOETL_SKIP_ENV_LOCAL=1
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
source "${SCRIPT_DIR}/support/token_validation.sh"

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"
mkdir -p "${NPM_CONFIG_CACHE}"
mcp_exit_if_validate_only "memory"

export MEMORY_FILE_PATH="${MEMORY_FILE_PATH:-${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json}"
exec npx -y "@modelcontextprotocol/server-memory@2026.1.26" "$@"
