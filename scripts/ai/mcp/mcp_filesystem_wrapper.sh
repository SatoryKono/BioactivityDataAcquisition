#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
mcp_exit_if_validate_only "filesystem"

if command -v cygpath >/dev/null 2>&1; then
  wrapper="$(cygpath -aw "${SCRIPT_DIR}/mcp_filesystem_wrapper.ps1")"
elif command -v wslpath >/dev/null 2>&1; then
  wrapper="$(wslpath -aw "${SCRIPT_DIR}/mcp_filesystem_wrapper.ps1")"
else
  printf '%s\n' 'Filesystem MCP requires the registered Windows owner.' >&2
  exit 1
fi
if ! command -v powershell.exe >/dev/null 2>&1; then
  printf '%s\n' 'Filesystem MCP requires the registered Windows owner.' >&2
  exit 1
fi
exec powershell.exe -NoProfile -NonInteractive -File "${wrapper}"
