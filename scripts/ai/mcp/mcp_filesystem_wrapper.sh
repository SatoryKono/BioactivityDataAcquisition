#!/usr/bin/env bash
# MCP filesystem server: pin package and scope to repo root with a host-native
# absolute path. Avoids client-side expansion of portable "." into a foreign
# OS path (e.g. Windows E:\... under WSL Node), which breaks path.resolve().
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"
mkdir -p "${NPM_CONFIG_CACHE}"

# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
mcp_exit_if_validate_only "filesystem"

# Optional extra allowed roots after the repo root (advanced clients).
exec npx -y "@modelcontextprotocol/server-filesystem@2026.1.14" "${REPO_ROOT}" "$@"
