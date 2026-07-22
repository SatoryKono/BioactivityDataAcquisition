#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
export UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"

# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
mcp_exit_if_validate_only "mcp-code-interpreter"

if command -v python3 >/dev/null 2>&1; then
  if python3 -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('mcp_server_code_interpreter') else 1)"; then
    exec python3 -m mcp_server_code_interpreter "$@"
  fi
fi

if command -v uvx >/dev/null 2>&1; then
  if uvx mcp-server-code-interpreter --stdio "$@"; then
    exit 0
  fi
fi

if command -v python3 >/dev/null 2>&1; then
  if python3 -m uv mcp-server-code-interpreter --stdio "$@"; then
    exit 0
  fi
fi

# Last-resort npm candidates (names vary by publisher; may 404).
if npx -y mcp-server-code-interpreter --stdio "$@"; then
  exit 0
fi

printf '%s\n' \
  "mcp-code-interpreter could not start." \
  "Install mcp-server-code-interpreter (pip/uv) or ensure uvx is on PATH." >&2
exit 1
