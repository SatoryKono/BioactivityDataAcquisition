#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

# MCP server packages (not plain @ast-grep/cli).
if npx -y @notprolands/ast-grep-mcp --stdio "$@"; then
  exit 0
fi

exec npx -y @chousyn/ast-grep-mcp --stdio "$@"
